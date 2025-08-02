#!/usr/bin/env python3
"""
Mock GitLab Server for Testing
==============================

A mock HTTP server that simulates GitLab API responses for testing
the issue queue bot without making real API calls.
"""

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import queue
from typing import Dict, Any, List

class MockGitLabState:
    """Maintains state for the mock GitLab server."""
    
    def __init__(self):
        self.issues = {}  # iid -> issue data
        self.merge_requests = {}  # iid -> MR data
        self.issue_closed_by = {}  # issue_iid -> [mr_data]
        self.next_issue_iid = 1
        self.next_mr_iid = 1
        self.project_id = "12345"
        
    def create_issue(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new issue."""
        issue = {
            "iid": self.next_issue_iid,
            "id": self.next_issue_iid * 100,
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "state": "opened",
            "labels": data.get("labels", []),
            "assignee_ids": data.get("assignee_ids", []),
            "web_url": f"https://mock-gitlab.com/project/issues/{self.next_issue_iid}",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        }
        
        self.issues[self.next_issue_iid] = issue
        self.next_issue_iid += 1
        
        return issue
    
    def close_issue(self, iid: int, mr_iid: int = None) -> Dict[str, Any]:
        """Close an issue, optionally with an MR."""
        if iid not in self.issues:
            raise ValueError(f"Issue {iid} not found")
        
        self.issues[iid]["state"] = "closed"
        
        if mr_iid:
            # Create MR if it doesn't exist
            if mr_iid not in self.merge_requests:
                self.merge_requests[mr_iid] = {
                    "iid": mr_iid,
                    "id": mr_iid * 200,
                    "state": "opened",
                    "title": f"Fix for issue #{iid}",
                    "web_url": f"https://mock-gitlab.com/project/merge_requests/{mr_iid}"
                }
            
            # Record that this MR closed the issue
            self.issue_closed_by[iid] = [self.merge_requests[mr_iid]]
        
        return self.issues[iid]
    
    def merge_mr(self, iid: int) -> Dict[str, Any]:
        """Merge a merge request."""
        if iid not in self.merge_requests:
            raise ValueError(f"MR {iid} not found")
        
        self.merge_requests[iid]["state"] = "merged"
        return self.merge_requests[iid]

class MockGitLabHandler(BaseHTTPRequestHandler):
    """HTTP request handler for mock GitLab API."""
    
    def __init__(self, state: MockGitLabState, *args, **kwargs):
        self.state = state
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass
    
    def do_GET(self):
        """Handle GET requests."""
        path = urlparse(self.path).path
        params = parse_qs(urlparse(self.path).query)
        
        try:
            if path == "/api/v4/user":
                self._send_json({"id": 1, "name": "Test User", "username": "testuser"})
            
            elif path == f"/api/v4/projects/{self.state.project_id}":
                self._send_json({
                    "id": self.state.project_id,
                    "name": "Test Project",
                    "web_url": "https://mock-gitlab.com/project"
                })
            
            elif path == f"/api/v4/projects/{self.state.project_id}/issues":
                self._handle_list_issues(params)
            
            elif path.startswith(f"/api/v4/projects/{self.state.project_id}/issues/") and path.endswith("/closed_by"):
                issue_iid = int(path.split("/")[-2])
                closed_by = self.state.issue_closed_by.get(issue_iid, [])
                self._send_json(closed_by)
            
            elif path.startswith(f"/api/v4/projects/{self.state.project_id}/issues/"):
                issue_iid = int(path.split("/")[-1])
                if issue_iid in self.state.issues:
                    self._send_json(self.state.issues[issue_iid])
                else:
                    self._send_error(404, "Issue not found")
            
            elif path.startswith(f"/api/v4/projects/{self.state.project_id}/merge_requests/"):
                mr_iid = int(path.split("/")[-1])
                if mr_iid in self.state.merge_requests:
                    self._send_json(self.state.merge_requests[mr_iid])
                else:
                    self._send_error(404, "MR not found")
            
            else:
                self._send_error(404, "Not found")
                
        except Exception as e:
            self._send_error(500, str(e))
    
    def do_POST(self):
        """Handle POST requests."""
        path = urlparse(self.path).path
        
        try:
            if path == f"/api/v4/projects/{self.state.project_id}/issues":
                content_length = int(self.headers['Content-Length'])
                data = json.loads(self.rfile.read(content_length).decode('utf-8'))
                issue = self.state.create_issue(data)
                self._send_json(issue, status=201)
            else:
                self._send_error(404, "Not found")
                
        except Exception as e:
            self._send_error(500, str(e))
    
    def do_PUT(self):
        """Handle PUT requests."""
        path = urlparse(self.path).path
        
        try:
            if path.startswith(f"/api/v4/projects/{self.state.project_id}/issues/"):
                issue_iid = int(path.split("/")[-1])
                content_length = int(self.headers['Content-Length'])
                data = json.loads(self.rfile.read(content_length).decode('utf-8'))
                
                if data.get("state_event") == "close":
                    issue = self.state.close_issue(issue_iid)
                    self._send_json(issue)
                else:
                    self._send_error(400, "Unsupported operation")
            else:
                self._send_error(404, "Not found")
                
        except Exception as e:
            self._send_error(500, str(e))
    
    def _handle_list_issues(self, params: Dict[str, List[str]]):
        """Handle issue listing with filtering."""
        issues = list(self.state.issues.values())
        
        # Filter by labels
        if "labels" in params:
            label_filter = params["labels"][0]
            issues = [issue for issue in issues if label_filter in issue.get("labels", [])]
        
        # Sort by created_at desc
        if params.get("order_by", [""])[0] == "created_at" and params.get("sort", [""])[0] == "desc":
            issues.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Limit results
        per_page = int(params.get("per_page", ["20"])[0])
        issues = issues[:per_page]
        
        self._send_json(issues)
    
    def _send_json(self, data: Any, status: int = 200):
        """Send JSON response."""
        response = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)
    
    def _send_error(self, status: int, message: str):
        """Send error response."""
        error_data = {"message": message}
        self._send_json(error_data, status)

class MockGitLabServer:
    """Mock GitLab server for testing."""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.state = MockGitLabState()
        self.server = None
        self.thread = None
    
    def start(self):
        """Start the mock server."""
        def handler(*args, **kwargs):
            return MockGitLabHandler(self.state, *args, **kwargs)
        
        self.server = HTTPServer(('localhost', self.port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        
        print(f"🚀 Mock GitLab server started on http://localhost:{self.port}")
    
    def stop(self):
        """Stop the mock server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join()
        print("🛑 Mock GitLab server stopped")
    
    def reset(self):
        """Reset server state."""
        self.state = MockGitLabState()
    
    def create_scenario_issue_with_merged_mr(self) -> tuple[int, int]:
        """Create a test scenario: issue closed by merged MR."""
        # Create issue
        issue = self.state.create_issue({
            "title": "Test Issue",
            "description": "Test description",
            "labels": ["auto-generated"]
        })
        
        # Create and merge MR
        mr_iid = self.state.next_mr_iid
        self.state.next_mr_iid += 1
        
        # Close issue with MR
        self.state.close_issue(issue["iid"], mr_iid)
        
        # Merge the MR
        self.state.merge_mr(mr_iid)
        
        return issue["iid"], mr_iid
    
    def create_scenario_issue_with_unmerged_mr(self) -> tuple[int, int]:
        """Create a test scenario: issue closed by unmerged MR."""
        # Create issue
        issue = self.state.create_issue({
            "title": "Test Issue 2",
            "description": "Test description",
            "labels": ["auto-generated"]
        })
        
        # Create MR but don't merge
        mr_iid = self.state.next_mr_iid
        self.state.next_mr_iid += 1
        
        # Close issue with MR
        self.state.close_issue(issue["iid"], mr_iid)
        
        # Don't merge the MR (leave it open)
        
        return issue["iid"], mr_iid

if __name__ == "__main__":
    # Demo the mock server
    server = MockGitLabServer(8080)
    
    try:
        server.start()
        
        # Create some test scenarios
        print("\n📝 Creating test scenarios...")
        
        issue1, mr1 = server.create_scenario_issue_with_merged_mr()
        print(f"✅ Created issue #{issue1} closed by merged MR !{mr1}")
        
        issue2, mr2 = server.create_scenario_issue_with_unmerged_mr()
        print(f"🟡 Created issue #{issue2} closed by unmerged MR !{mr2}")
        
        print(f"\n🌐 Server running at http://localhost:8080")
        print("📚 Available endpoints:")
        print("  GET /api/v4/user")
        print("  GET /api/v4/projects/12345")
        print("  GET /api/v4/projects/12345/issues")
        print("  POST /api/v4/projects/12345/issues")
        print("  GET /api/v4/projects/12345/issues/{iid}")
        print("  GET /api/v4/projects/12345/issues/{iid}/closed_by")
        print("  GET /api/v4/projects/12345/merge_requests/{iid}")
        
        print("\nPress Ctrl+C to stop the server...")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping server...")
    finally:
        server.stop()
