pragma solidity ^0.4.18;

contract QuantstampAuditInternal {
  /**
    * @dev Audit report contains the auditor address and the actual report
    */
  struct AuditReport {
    uint256 requestId;
    address auditor;
    string report;
  }

  // keeps track of audits
  mapping(address => mapping(string => AuditReport)) private auditReports;

  event LogAuditRequested(uint256 requestId, address requestor, string uri, uint256 price);
  event LogReportSubmitted(uint256 requestId, address auditor, address requestor, string uri);

  function doAudit(uint256 requestId, address requestor, string uri, uint256 price) external {
    LogAuditRequested(requestId, requestor, uri, price);
  }

  function submitReport(uint256 requestId, address requestor, string uri, string report) public {
    // verify that the report hasn't been issued yet
    require(!isAudited(requestor, uri));
    // TODO: use audit id to distinguish requests
    auditReports[requestor][uri] = AuditReport(requestId, msg.sender, report);
    LogReportSubmitted(requestId, msg.sender, requestor, uri);
  }

  function isAudited(address requestor, string uri) public constant returns(bool) {
    return auditReports[requestor][uri].auditor != address(0);
  }
}
