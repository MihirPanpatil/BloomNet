import os, time, logging, json, io
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, Depends
import requests, jwt
from minio import Minio
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware


def _required(name: str) -> str:
    """Read a required secret from the environment. There are no built-in defaults."""
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is not set. Copy .env.example to .env and fill it in.")
    return value



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("datanode")

NODE_ID = os.environ.get('NODE_ID','dnode')
PARENT_KERNEL = os.environ.get('PARENT_KERNEL','http://localhost:8001')
MART_ID = os.environ.get('MART_ID','default')
NODE_TOKEN = os.environ.get('NODE_TOKEN','') # token issued by kernel for this node
KERNEL_JWT_SECRET = _required('KERNEL_JWT_SECRET')

MINIO_ENDPOINT = os.environ.get('MINIO_ENDPOINT','minio:9000')
MINIO_ACCESS = _required('MINIO_ACCESS')
MINIO_SECRET = _required('MINIO_SECRET')

DATA_DIR = '/data'
os.makedirs(DATA_DIR, exist_ok=True)
META_FILE = os.path.join(DATA_DIR, 'metadata.json')


# init meta
if os.path.exists(META_FILE):
    with open(META_FILE,'r') as f:
        metadata = json.load(f)
else:
    metadata = {}


# minio client
minio_client = Minio(
    endpoint=MINIO_ENDPOINT,
    access_key=MINIO_ACCESS,
    secret_key=MINIO_SECRET,
    secure=False
)

app = FastAPI(title=f"DataNode {NODE_ID}")

# token verify (accept kernel tokens with role kernel, or node/portal tokens as needed)
def verify_token(header: str = Header(None)):
    if not header:
        raise HTTPException(status_code=401, detail='Missing Authorization header')
    scheme, _, token = header.partition(' ')
    try:
        payload = jwt.decode(token, KERNEL_JWT_SECRET, algorithms=['HS256'])
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f'Invalid token: {e}')



# startup: register with kernel (use NODE_TOKEN as Authorization)
@app.on_event("startup")
def startup_register():
    if not NODE_TOKEN:
        logger.warning("NODE_TOKEN empty - skipping registration.")
        return
    payload = {'node_id': NODE_ID, 'node_ip': NODE_ID, 'marts': [MART_ID]}
    headers = {'Authorization': f'Bearer {NODE_TOKEN}', 'Content-Type': 'application/json'}
    try:
        r = requests.post(f"{PARENT_KERNEL}/register_datanode", json=payload, headers=headers, timeout=5)
        logger.info(f"Registration response: {r.status_code} {r.text}")
    except Exception as e:
        logger.warning(f"Registration failed: {e}")



@app.post("/write")
async def write_file(
    key: str = Form(..., min_length=1, max_length=1024, regex=r'^[a-zA-Z0-9_\-\./]+$'),
    file: UploadFile = File(...)
):
    """
    Handle file upload to this datanode.
    
    Args:
        key: Unique identifier for the file (alphanumeric, underscores, hyphens, dots, and slashes)
        file: The file to upload
        
    Returns:
        dict: Status of the operation
    """
    # Validate file size (e.g., 100MB max)
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    try:
        content = await file.read(MAX_FILE_SIZE + 1)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f'File too large. Maximum size is {MAX_FILE_SIZE} bytes')
            
        # Validate file type if needed
        # allowed_types = ['image/jpeg', 'application/pdf']  # Example
        # if file.content_type not in allowed_types:
        #     raise HTTPException(status_code=400, detail=f'Unsupported file type: {file.content_type}')
        
        bucket = f"mart-{MART_ID}"
        
        # Ensure bucket exists
        try:
            if not minio_client.bucket_exists(bucket):
                minio_client.make_bucket(bucket)
                logger.info(f"Created bucket: {bucket}")
        except Exception as e:
            logger.error(f"MinIO bucket error for {bucket}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f'Failed to access storage bucket: {str(e)}'
            )
        
        # Check if file already exists
        try:
            if key in metadata:
                logger.warning(f"File with key '{key}' already exists in mart '{MART_ID}'")
                # Option 1: Return error
                # raise HTTPException(status_code=409, detail='File with this key already exists')
                # Option 2: Overwrite (current behavior)
                pass
        except Exception as e:
            logger.error(f"Metadata check failed: {str(e)}")
        
        # Upload to MinIO
        try:
            data_stream = io.BytesIO(content)
            minio_client.put_object(
                bucket_name=bucket,
                object_name=key,
                data=data_stream,
                length=len(content),
                content_type=file.content_type or 'application/octet-stream',
                metadata={
                    'original-filename': file.filename,
                    'content-type': file.content_type or 'application/octet-stream',
                    'uploaded-by': NODE_ID,
                    'upload-timestamp': datetime.utcnow().isoformat()
                }
            )
            logger.info(f"Successfully uploaded {key} to {bucket}")
        except Exception as e:
            logger.error(f"MinIO upload failed for {key}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f'Failed to upload file: {str(e)}'
            )
        
        # Notify kernel about the uploaded object
        try:
            response = requests.post(
                f"{PARENT_KERNEL}/object_uploaded",
                json={'mart': MART_ID, 'key': key},
                timeout=10
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to notify kernel about {key}: {str(e)}")
            # Continue even if notification fails, as the file is already in MinIO
        
        # Update local metadata
        try:
            metadata[key] = {
                'mart': MART_ID,
                'stored_by': NODE_ID,
                'filename': file.filename,
                'content_type': file.content_type,
                'size': len(content),
                'uploaded_at': datetime.utcnow().isoformat(),
                'stored_locally': False,
                'bucket': bucket
            }
            with open(META_FILE, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to update metadata for {key}: {str(e)}")
            # Don't fail the request if metadata update fails
        
        return {
            'status': 'success',
            'key': key,
            'node': NODE_ID,
            'mart': MART_ID,
            'size': len(content),
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in write_file: {str(e)}")
        raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')



@app.post("/pull")
def pull_from_minio(body: dict):
    """
    Notes about datanode code
    At startup the datanode will try to register with PARENT_KERNEL using
    NODE_TOKEN as Authorization. The kernel must have issued this token
    (instructions below).
    write uploads to MinIO, then triggers object_uploaded on the kernel. Kernel
    will call pull on the parent node (this node) to fetch the object locally and then
    Kernel instructs this node to fetch object from MinIO and store locally.
    Body: { "mart": "...", "key": "..." }
    """
    mart = body.get('mart'); key = body.get('key')
    if not mart or not key:
        raise HTTPException(status_code=400, detail='mart & key required')
    bucket = f"mart-{mart}"
    try:
        local_file = os.path.join(DATA_DIR, f"{mart}__{key}")
        # download
        minio_client.fget_object(bucket, key, local_file)
        metadata[key] = {'mart': mart, 'path': local_file, 'stored_by': NODE_ID, 'ts': time.time(),'stored_locally': True}
        with open(META_FILE,'w') as f:
            json.dump(metadata, f, indent=2)
        return {'status':'ok', 'node': NODE_ID}
    except Exception as e:
        logger.error("pull_from_minio error: " + str(e))
        raise HTTPException(status_code=500, detail='pull failed')


@app.post("/sync")
def sync_object(body: dict):
    # same as pull_from_minio (child receives a directive from parent to pull)
    return pull_from_minio(body)


@app.get('/inventory')
def inventory():
    return metadata


@app.get('/health')
def health():
    return {'status': 'ok', 'node': NODE_ID, 'stored_objects': len(metadata)}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only, restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)