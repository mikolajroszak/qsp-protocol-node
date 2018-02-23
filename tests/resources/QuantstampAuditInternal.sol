pragma solidity 0.4.18;

import "./Queue.sol";

contract QuantstampAuditInternal {

  enum AuditRequestState {
    None, // 0
    Queued, // 1
    Assigned, // 2
    Completed // 3
  }  

  /**
    * @dev AuditRequest contains the requestor address, the request uri, and the price
    */  
  struct AuditRequest {
    address requestor;
    string uri;
    uint256 price;
    AuditRequestState state;
    address auditor;
  }

  /**
    * @dev Audit report contains the auditor address and the actual report
    */
  struct AuditReport {
    uint256 requestId;
    address auditor;
    string report;
  }

  // keeps track of audit requests
  mapping(uint256 => AuditRequest) private auditRequests;
  // keeps track of audit reports
  mapping(uint256 => AuditReport) private auditReports;

  event LogAuditRequested(uint256 requestId, address requestor, string uri, uint256 price);
  event LogAuditRequestAssigned(uint256 requestId, address auditor, address requestor, string uri, uint256 price);
  event LogReportSubmitted(uint256 requestId, address auditor, address requestor, string uri, string report);
  event LogAuditAlreadyExists(uint256 requestId);
  event LogReportSubmissionError_InvalidAuditor(uint256 requestId, address auditor);
  event LogReportSubmissionError_InvalidState(uint256 requestId, AuditRequestState state);
  event LogErrorAlreadyAudited(uint256 requestId, address requestor, string uri);
  event LogUnableToQueueAudit(uint256 requestId, address requestor, string uri);
  event LogAuditQueueIsEmpty();
  
  Uint256Queue requestQueue;
  uint constant REQUEST_QUEUE_CAPACITY = 30000;
  
  function QuantstampAuditInternal() public {
    requestQueue = new Uint256Queue(REQUEST_QUEUE_CAPACITY);
  }
  
  function doAudit(uint256 requestId, address requestor, string uri, uint256 price) public {    
    //TODO: rename to queueAudit(...). Kept for compatibility with the Gateway node
    if (auditRequests[requestId].state != AuditRequestState.None) {
      LogAuditAlreadyExists(requestId);
      return;
    }

    if (requestQueue.push(requestId) != Uint256Queue.PushResult.Success) {
      LogUnableToQueueAudit(requestId, requestor, uri);
      return;
    }
    auditRequests[requestId] = AuditRequest(requestor, uri, price, AuditRequestState.Queued, address(0));
    LogAuditRequested(requestId, requestor, uri, price);
    // TODO: rename to LogAuditQueued(...). Kept for compatibility with the Audit node
  }

  function getNextAuditRequest() public {
    Uint256Queue.PopResult popResult;
    uint256 requestId;
    
    (popResult, requestId) = requestQueue.pop();
    if (popResult == Uint256Queue.PopResult.QueueIsEmpty) {      
      LogAuditQueueIsEmpty();
      return;
    }
    auditRequests[requestId].state = AuditRequestState.Assigned;
    auditRequests[requestId].auditor = msg.sender;
    
    LogAuditRequestAssigned(
      requestId,
      auditRequests[requestId].auditor,
      auditRequests[requestId].requestor, 
      auditRequests[requestId].uri,
      auditRequests[requestId].price
    );
  }

  function submitReport(uint256 requestId, address requestor, string uri, string report) public {
    if (auditRequests[requestId].state == AuditRequestState.Completed) {
      LogReportSubmissionError_InvalidState(requestId, auditRequests[requestId].state);
      return;
    }
    
    auditReports[requestId] = AuditReport(requestId, msg.sender, report);
    auditRequests[requestId].state = AuditRequestState.Completed;
    LogReportSubmitted(requestId, msg.sender, requestor, uri, report);
  }

  function getAuditState(uint256 requestId) public constant returns(AuditRequestState) {
    return auditRequests[requestId].state;
  }
  
  function getQueueLength() public constant returns(uint) {
    return requestQueue.length();
  }
  
  function getQueueCapacity() public constant returns(uint) {
    return requestQueue.capacity();
  }
}