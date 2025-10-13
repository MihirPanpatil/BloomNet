import os, json, time, logging, requests, jwt
from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from minio import Minio
from datetime import timedelta, datetime
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kernel")

# config from env
DATA_FILE = '/app/data/registry.json'
os.makedirs('/app/data', exist_ok=True)
SECRET = os.environ.get('KERNEL_JWT_SECRET', 'devsecret')
PEERS = os.environ.get('PEER_KERNELS','').split(',') if os.environ.get('PEER_KERNELS') else []
MINIO_ENDPOINT = os.environ.get('MINIO_ENDPOINT','minio:9000')
MINIO_ACCESS = os.environ.get('MINIO_ACCESS','minioadmin')
MINIO_SECRET = os.environ.get('MINIO_SECRET','minioadmin')

# Minio client (used for presigns)
minio_client = Minio(
    endpoint=MINIO_ENDPOINT, # Use the internal Docker address for connection
    access_key=MINIO_ACCESS,
    secret_key=MINIO_SECRET,
    secure=False
)

# Minio client for generating browser-accessible presigned URLs
minio_client_external = Minio(
    endpoint="192.168.1.1:9000", # Use Docker host IP for browser presigned URLs
    access_key=MINIO_ACCESS,
    secret_key=MINIO_SECRET,
    secure=False
)


# registry structure
if os.path.exists(DATA_FILE):
    with open(DATA_FILE,'r') as f:
        registry = json.load(f)
else:
    registry = {'nodes':{}, 'marts':{}}

app = FastAPI(title="Bloom Kernel")

# Add CORS middleware to allow requests from specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Restrict to portal origin only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Log the incoming request
    logger.info(f"Incoming request: {request.method} {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")
    
    # Check for Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header:
        logger.info(f"Authorization header present: {auth_header[:20]}...")
    else:
        logger.warning("No Authorization header found in request")
    
    # Process the request
    response = await call_next(request)
    
    # Log the response
    logger.info(f"Response status: {response.status_code}")
    return response

# utilities
def save_registry():
    with open(DATA_FILE,'w') as f:
        json.dump(registry, f, indent=2)

def issue_token(sub: str, role: str='node', exp_seconds: int=3600):
    payload = {'sub': sub, 'role': role, 'iat': int(time.time()), 'exp': int(time.time()) + exp_seconds}
    return jwt.encode(payload, SECRET, algorithm='HS256')

def verify_token(header: str = Header(None, alias="Authorization")):
    logger.info(f"verify_token called with header: {header}")
    if not header:
        logger.warning("No Authorization header provided")
        raise HTTPException(status_code=401, detail='Missing Authorization header')
    
    # Log the first 10 chars of the token for debugging (don't log the whole token for security)
    logger.info(f"Authorization header value starts with: {header[:10]}...")
    
    scheme, _, token = header.partition(' ')
    if scheme.lower() != 'bearer':
        logger.warning(f"Invalid authorization scheme: {scheme}")
        raise HTTPException(status_code=401, detail='Invalid authorization scheme. Use Bearer token')
    
    if not token:
        logger.warning("No token provided after Bearer")
        raise HTTPException(status_code=401, detail='No token provided')
    
    try:
        logger.info("Decoding JWT token...")
        payload = jwt.decode(token, SECRET, algorithms=['HS256'])
        logger.info(f"Token payload: {payload}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise HTTPException(status_code=401, detail='Token has expired')
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(status_code=401, detail=f'Invalid token: {e}')
    except Exception as e:
        logger.error(f"Unexpected error verifying token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail='Internal server error during token verification')

# small dev-only endpoint to generate tokens (useful to generate NODE_TOKENs prior to starting datanodes)
@app.post('/auth/generate')
async def auth_generate(body: dict):
    """
    Dev helper: POST {"sub":"node:photos-parent","role":"node","exp_seconds":86400}
    Returns: {"token": "..."}
    CAUTION: Only available when DEV_MODE=true environment variable is set.
    """
    # Check if DEV_MODE is enabled
    dev_mode = os.environ.get('DEV_MODE', 'false').lower() == 'true'
    if not dev_mode:
        raise HTTPException(
            status_code=404,
            detail='Endpoint not found. This endpoint is only available in development mode.'
        )

    sub = body.get('sub')
    role = body.get('role','node')
    exp = int(body.get('exp_seconds', 86400))
    token = issue_token(sub, role, exp)
    return {'token': token}


class RegisterPayload(BaseModel):
    node_id: str
    node_ip: str
    marts: list = []


@app.post('/register_datanode')
async def register_datanode(payload: RegisterPayload, auth=Depends(verify_token), propagate: bool = True):
    """
    Register a datanode. 
    """
    # allow nodes and kernels to register
    role = auth.get('role')
    if role not in ('node','kernel','admin'):
        raise HTTPException(status_code=403, detail='not allowed to register')
    registry['nodes'][payload.node_id] = {'ip': payload.node_ip, 'marts': payload.marts or [], 'last_seen': time.time()}
    # ensure mart entries exist
    for m in payload.marts:
        registry['marts'].setdefault(m, {'parent': None, 'children': []})
    save_registry()
    logger.info(f"Registered node {payload.node_id} ip={payload.node_ip} marts={payload.marts}")
    # propagate to peers if requested
    if propagate and PEERS:
        token = issue_token('kernel-propagation','kernel', exp_seconds=300)
        headers = {'Authorization': f'Bearer {token}'}
        for peer in PEERS:
            try:
                url = f"http://{peer}/register_datanode?propagate=false"
                requests.post(url, json=payload.dict(), headers=headers, timeout=3)
            except Exception as e:
                logger.warning(f"Failed to propagate to {peer}: {e}")
    return {'status':'ok'}


class MartDecl(BaseModel):
    mart_id: str
    parent: str
    children: list


@app.post('/declare_mart')
async def declare_mart(m: MartDecl, auth=Depends(verify_token), propagate: bool = True):
    """
    Declare a mart. 
    """
    # only admin or kernel role allowed
    role = auth.get('role')
    if role not in ('admin','kernel'):
        raise HTTPException(status_code=403, detail='not allowed to declare_mart')
    registry['marts'][m.mart_id] = {'parent': m.parent, 'children': m.children}
    save_registry()
    logger.info(f"Declared mart {m.mart_id} parent={m.parent} children={m.children}")
    # propagate to peers
    if propagate and PEERS:
        token = issue_token('kernel-propagation','kernel', exp_seconds=300)
        headers = {'Authorization': f'Bearer {token}'}
        for peer in PEERS:
            try:
                url = f"http://{peer}/declare_mart?propagate=false"
                requests.post(url, json=m.dict(), headers=headers, timeout=3)
            except Exception as e:
                logger.warning(f"Failed to propagate mart to {peer}: {e}")
    return {'status':'ok'}


@app.get('/registry')
async def get_registry():
    return registry


@app.get('/health')
async def health():
    return {'status': 'ok', 'kernels': len(PEERS) + 1, 'marts': len(registry['marts']), 'nodes': len(registry['nodes'])}


@app.get('/mart/{mart_id}')
async def get_mart(mart_id: str):
    if mart_id not in registry['marts']:
        raise HTTPException(status_code=404, detail='mart not found')
    return registry['marts'][mart_id]


# presign upload for portal - NO AUTH REQUIRED
@app.post('/presign_upload')
async def presign_upload(body: dict):
    """
    Presign a URL for uploading a file to MinIO.
    """
    try:
        mart = body.get('mart')
        key = body.get('key')
        logger.info(f"Received presign request for mart={mart}, key={key}")

        if not mart or not key:
            raise HTTPException(status_code=400, detail='mart and key required')

        bucket = f"mart-{mart}"
        logger.info(f"Using bucket: {bucket}")

        # Ensure bucket exists
        try:
            if not minio_client.bucket_exists(bucket):
                logger.info(f"Creating bucket: {bucket}")
                minio_client.make_bucket(bucket)
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetObject", "s3:PutObject"],
                            "Resource": [f"arn:aws:s3:::{bucket}/*"]
                        }
                    ]
                }
                minio_client.set_bucket_policy(bucket, json.dumps(policy))
                logger.info(f"Applied public read/write policy to bucket: {bucket}")
        except Exception as e:
            logger.error(f"Error with bucket {bucket}: {str(e)}")
            raise HTTPException(status_code=500, detail=f'Error with bucket: {str(e)}')

        # presigned PUT (1 hour)
        expires = timedelta(hours=1)
        try:
            logger.info("Generating pre-signed URL...")

            # Generate presigned URL using external client (browser-accessible)
            url = minio_client_external.presigned_put_object(
                bucket,
                key,
                expires=expires
            )

            # Replace Docker host IP with localhost for browser access
            url = url.replace("192.168.1.1:9000", "localhost:9000")
            logger.info(f"Generated URL: {url}")
            return {"url": url}

        except Exception as e:
            logger.error(f"Error generating pre-signed URL: {str(e)}")
            raise HTTPException(status_code=500, detail=f'Error generating pre-signed URL: {str(e)}')

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in presign_upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')
# kernel gets notified when an object was uploaded - NO AUTH REQUIRED
@app.post('/object_uploaded')
async def object_uploaded(body: dict):
    """
    Handle notification that a new object was uploaded to MinIO.
    This endpoint is called by datanodes after they upload a file to MinIO.
    The kernel then coordinates with the appropriate parent node to pull the file.
    
    Args:
        body: Dictionary containing 'mart' and 'key' of the uploaded object
        
    Returns:
        dict: Status of the operation
    """
    # Input validation
    mart = body.get('mart')
    key = body.get('key')
    
    if not mart or not key:
        logger.warning("object_uploaded called with missing parameters")
        raise HTTPException(
            status_code=400, 
            detail='Both "mart" and "key" parameters are required'
        )
    
    # Log the notification
    logger.info(f"Received object_uploaded notification: mart={mart}, key={key}")
    
    # Check if mart exists
    if mart not in registry['marts']:
        logger.error(f"Mart '{mart}' not found in registry")
        raise HTTPException(
            status_code=404, 
            detail=f'Mart "{mart}" is not declared. Please declare the mart first.'
        )
    
    # Get parent node info
    parent_id = registry['marts'][mart].get('parent')
    if not parent_id:
        logger.error(f"No parent defined for mart '{mart}'")
        raise HTTPException(
            status_code=500, 
            detail=f'No parent node defined for mart "{mart}"'
        )
    
    if parent_id not in registry['nodes']:
        logger.error(f"Parent node '{parent_id}' not found in registry")
        raise HTTPException(
            status_code=500, 
            detail=f'Parent node "{parent_id}" is not registered or unavailable'
        )
    
    parent_info = registry['nodes'][parent_id]
    parent_ip = parent_info.get('ip')
    
    if not parent_ip:
        logger.error(f"Parent node '{parent_id}' has no IP address")
        raise HTTPException(
            status_code=500,
            detail=f'Parent node "{parent_id}" has no valid IP address'
        )
    
    # Prepare the request to the parent node
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Call parent's /pull endpoint to have it fetch the object from MinIO
    try:
        pull_url = f"http://{parent_ip}:8000/pull"
        logger.debug(f"Instructing parent {parent_id} to pull {mart}/{key} from {pull_url}")
        
        # Add timeout and retry logic
        max_retries = 3
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    pull_url,
                    json={'mart': mart, 'key': key},
                    headers=headers,
                    timeout=15  # 15 second timeout
                )
                response.raise_for_status()
                logger.info(f"Successfully instructed parent {parent_id} to pull {mart}/{key}")
                return {
                    'status': 'success',
                    'message': f'Successfully instructed parent {parent_id} to pull the file',
                    'mart': mart,
                    'key': key,
                    'parent': parent_id
                }
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed for {pull_url}: {str(e)}. "
                    f"Retrying in {wait_time} seconds..."
                )
                time.sleep(wait_time)
        
        # If we get here, all retries failed
        error_msg = f"All {max_retries} attempts to contact parent {parent_id} failed: {str(last_exception)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=502,
            detail=f'Failed to contact parent node after {max_retries} attempts: {str(last_exception)}'
        )
        
    except Exception as e:
        logger.exception(f"Unexpected error in object_uploaded: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f'Internal server error while processing upload: {str(e)}'
        )
    return {'status':'ok', 'parent': parent_id}