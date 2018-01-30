pragma solidity 0.4.18;

contract QuantstampAuditInternal {

  /**
    * @dev Audit report contains the auditor address and the actual report
    */
  struct AuditReport {
    address auditor;
    string report;
  }

  // keeps track of audits
  mapping(address => mapping(string => AuditReport)) private auditReports;

  event LogAuditRequested(address requestor, string uri, uint256 price);
  event LogReportSubmitted(address auditor, address requestor, string uri);

  function doAudit(address requestor, string uri, uint256 price) external {
    LogAuditRequested(requestor, uri, price);
  }

  function submitReport(address requestor, string uri, string report) external {
    // verify that the report hasn't been issued yet
    require(!isAudited(requestor, uri));
    // TODO: use audit id to distinguish requests
    auditReports[requestor][uri] = AuditReport(msg.sender, report);
    LogReportSubmitted(msg.sender, requestor, uri);
  }

  function isAudited(address requestor, string uri) public constant returns(bool) {
    return auditReports[requestor][uri].auditor != address(0);
  }
}