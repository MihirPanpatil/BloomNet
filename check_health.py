#!/usr/bin/env python3
import os
import sys
import json
import requests
import argparse
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

# Configuration
SERVICES = {
    'kernels': [
        {'name': 'Kernel 1', 'url': 'http://localhost:8001/health'},
        {'name': 'Kernel 2', 'url': 'http://localhost:8002/health'},
        {'name': 'Kernel 3', 'url': 'http://localhost:8003/health'},
    ],
    'datanodes': [
        # Photos mart
        {'name': 'Photos Parent', 'url': 'http://localhost:8101/health'},
        {'name': 'Photos Child A', 'url': 'http://localhost:8102/health'},
        {'name': 'Photos Child B', 'url': 'http://localhost:8103/health'},
        # Research mart
        {'name': 'Research Parent', 'url': 'http://localhost:8201/health'},
        {'name': 'Research Child A', 'url': 'http://localhost:8202/health'},
        {'name': 'Research Child B', 'url': 'http://localhost:8203/health'},
        # Clients mart
        {'name': 'Clients Parent', 'url': 'http://localhost:8301/health'},
        {'name': 'Clients Child A', 'url': 'http://localhost:8302/health'},
        {'name': 'Clients Child B', 'url': 'http://localhost:8303/health'},
    ],
    'storage': [
        {'name': 'MinIO', 'url': 'http://localhost:9000/minio/health/ready'},
    ],
    'portal': [
        {'name': 'Web Portal', 'url': 'http://localhost:3000/api/health'},
    ]
}

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def check_service(service: Dict[str, str], timeout: int = 5) -> Dict[str, Any]:
    """Check the health of a single service."""
    try:
        # Special handling for MinIO
        if 'minio' in service['url'].lower():
            response = requests.get(service['url'], timeout=timeout)
            is_ok = response.status_code == 200
            return {
                'name': service['name'],
                'status': 'healthy' if is_ok else 'unhealthy',
                'details': f"Status: {response.status_code}",
                'ok': is_ok
            }
        
        # Standard health check
        response = requests.get(service['url'], timeout=timeout)
        response.raise_for_status()
        data = response.json()
        
        return {
            'name': service['name'],
            'status': 'healthy',
            'details': data,
            'ok': True
        }
    except requests.exceptions.RequestException as e:
        return {
            'name': service['name'],
            'status': 'unreachable',
            'details': str(e),
            'ok': False
        }
    except json.JSONDecodeError as e:
        return {
            'name': service['name'],
            'status': 'invalid_response',
            'details': f"Invalid JSON response: {str(e)}",
            'ok': False
        }
    except Exception as e:
        return {
            'name': service['name'],
            'status': 'error',
            'details': f"Unexpected error: {str(e)}",
            'ok': False
        }

def check_registry() -> Dict[str, Any]:
    """Check the registry status from the first kernel."""
    try:
        registry_url = 'http://localhost:8001/registry'
        response = requests.get(registry_url, timeout=5)
        response.raise_for_status()
        registry = response.json()
        
        # Basic registry stats
        stats = {
            'nodes': len(registry.get('nodes', {})),
            'marts': len(registry.get('marts', {})),
            'marts_list': list(registry.get('marts', {}).keys())
        }
        
        return {
            'name': 'Registry',
            'status': 'healthy',
            'details': stats,
            'ok': True
        }
    except Exception as e:
        return {
            'status': 'error',
            'details': f"Failed to check registry: {str(e)}",
            'ok': False
        }

def print_status(service_type: str, results: List[Dict[str, Any]], verbose: bool = False):
    """Print the status of services in a formatted way."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{service_type.upper()}{Colors.ENDC}")
    print("-" * (len(service_type) + 2))
    
    all_ok = True
    for result in results:
        status = result['status']
        
        if status == 'healthy':
            status_str = f"{Colors.OKGREEN}✓ {status.upper()}{Colors.ENDC}"
        elif status == 'unreachable':
            status_str = f"{Colors.FAIL}✗ {status.upper()}{Colors.ENDC}"
            all_ok = False
        else:
            status_str = f"{Colors.WARNING}? {status.upper()}{Colors.ENDC}"
            all_ok = False
        
        print(f"{Colors.BOLD}{result['name']}:{Colors.ENDC} {status_str}")
        
        if verbose or not result.get('ok', False):
            if isinstance(result['details'], dict):
                details = json.dumps(result['details'], indent=2).replace("\n", "\n    ")
                print(f"    {details}")
            else:
                print(f"    {result['details']}")
    
    return all_ok

def main():
    parser = argparse.ArgumentParser(description='Check the health of BloomNet services')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed output')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    args = parser.parse_args()
    
    if args.no_color:
        # Disable colors
        for color in dir(Colors):
            if not color.startswith('_'):
                setattr(Colors, color, '')
    
    print(f"{Colors.HEADER}{Colors.BOLD}BloomNet Health Check{Colors.ENDC}\n")
    
    # Check all services
    all_services_ok = True
    
    # Check kernels
    kernel_results = [check_service(s) for s in SERVICES['kernels']]
    all_services_ok &= print_status("Kernels", kernel_results, args.verbose)
    
    # Check datanodes
    datanode_results = [check_service(s) for s in SERVICES['datanodes']]
    all_services_ok &= print_status("Datanodes", datanode_results, args.verbose)
    
    # Check storage
    storage_results = [check_service(s) for s in SERVICES['storage']]
    all_services_ok &= print_status("Storage", storage_results, args.verbose)
    
    # Check portal
    portal_results = [check_service(s) for s in SERVICES['portal']]
    all_services_ok &= print_status("Portal", portal_results, args.verbose)
    
    # Check registry
    registry_result = check_registry()
    registry_ok = print_status("Registry", [registry_result], args.verbose)
    all_services_ok &= registry_ok
    
    # Print summary
    print(f"\n{'-' * 40}")
    if all_services_ok:
        print(f"{Colors.OKGREEN}{Colors.BOLD}✓ All services are healthy{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}✗ Some services are not healthy{Colors.ENDC}")
    
    sys.exit(0 if all_services_ok else 1)

if __name__ == "__main__":
    main()
