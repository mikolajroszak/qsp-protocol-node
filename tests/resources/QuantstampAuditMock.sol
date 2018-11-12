/***************************************************************************************************
 *                                                                                                 *
 * (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,         *
 * modified, redistributed, or otherwise disseminated except to the extent expressly authorized by *
 * Quantstamp for credentialed users. This content and its use are governed by the Quantstamp      *
 * Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.     *
 *                                                                                                 *
 **************************************************************************************************/

pragma solidity 0.4.25;

// File: contracts/QuantstampAudit.sol
// For updating the protocol node to use the real QuantstampAudit contract,
// see notes in https://quantstamp.atlassian.net/browse/QSP-369.

contract QuantstampAuditData{
  uint256 public auditTimeoutInBlocks = 25;
  uint256 public maxAssignedRequests = 10;

  // map audit nodes to their minimum prices. Defaults to zero: the node accepts all requests.
  mapping(address => uint256) public minAuditPrice;

  event getMinAuditPrice_called();
  function getMinAuditPrice(address addr) public view returns(uint256){
    emit getMinAuditPrice_called();
    return minAuditPrice[addr];
  }

  function setMinAuditPrice(address auditor, uint256 price) public {
    minAuditPrice[auditor] = price;
  }

  constructor(){ }

  function isWhitelisted(address node) public view returns(bool) {
    return node != 0x0;
  }
}

contract QuantstampAudit {

  // mapping from an auditor address to the number of requests that it currently processes
  mapping(address => uint256) public assignedRequestCount;


  // state of audit requests submitted to the contract
  enum AuditState {
    None,
    Queued,
    Assigned,
    Refunded,
    Completed,  // automated audit finished successfully and the report is available
    Error       // automated audit failed to finish; the report contains detailed information about the error
  }

  // structure representing an audit
  struct Audit {
    address requestor;
    string contractUri;
    uint256 price;
    uint256 transactionFee;
    uint requestBlockNumber; // approximate time of when audit was requested
    AuditState state;
    address auditor;       // the address of the node assigned to the audit
    uint assignBlockNumber;  // approximate time of when audit was assigned
    string reportHash;     // stores the hash of audit report
    uint reportBlockNumber;  // approximate time of when the payment and the audit report were submitted
  }

  struct AuditData {
      uint256 auditTimeoutInBlocks;
      uint256 maxAssignedRequests;
  }
  QuantstampAuditData public auditData;

  event LogAuditFinished(
    uint256 requestId,
    address auditor,
    AuditState auditResult,
    string reportHash
  );

  event LogAuditRequested(uint256 requestId,
    address requestor,
    string uri,
    uint256 price
  );

  // TODO update the smart contract appropriately
  event LogAuditAssigned(uint256 requestId,
      address auditor,
      address requestor,
      string uri,
      uint256 price,
      uint256 requestBlockNumber);
  event LogReportSubmissionError_InvalidAuditor(uint256 requestId, address auditor);
  event LogReportSubmissionError_InvalidState(uint256 requestId, address auditor, AuditState state);
  event LogAuditQueueIsEmpty();

  event LogAuditAssignmentError_ExceededMaxAssignedRequests(address auditor);

  event LogPayAuditor(uint256 requestId, address auditor, uint256 amount);
  event LogTransactionFeeChanged(uint256 oldFee, uint256 newFee);
  event LogAuditNodePriceChanged(address auditor, uint256 amount);

  event LogRefund(uint256 requestId, address requestor, uint256 amount);
  event LogRefundInvalidRequestor(uint256 requestId, address requestor);
  event LogRefundInvalidState(uint256 requestId, AuditState state);
  event LogRefundInvalidFundsLocked(uint256 requestId, uint256 currentBlock, uint256 fundLockEndBlock);

  // the audit queue has elements, but none satisfy the minPrice of the audit node
  // amount corresponds to the current minPrice of the auditor
  event LogAuditNodePriceHigherThanRequests(address auditor, uint256 amount);

  constructor (address addr) public {
      auditData = QuantstampAuditData(addr);
  }

  function emitLogAuditFinished(uint256 requestId, address auditor, AuditState auditResult, string reportHash) {
    emit LogAuditFinished(requestId, auditor, auditResult, reportHash);
  }

  function emitLogAuditRequested(uint256 requestId, address requestor, string uri, uint256 price) {
    emit LogAuditRequested(requestId, requestor, uri, price);
  }

  function emitLogAuditAssigned(uint256 requestId, address auditor, address requestor, string uri, uint256 price, uint256 requestBlockNumber) {
    emit LogAuditAssigned(requestId, auditor, requestor, uri, price, requestBlockNumber);
  }

  function emitLogReportSubmissionError_InvalidAuditor(uint256 requestId, address auditor) {
    emit LogReportSubmissionError_InvalidAuditor(requestId, auditor);
  }

  function emitLogReportSubmissionError_InvalidState(uint256 requestId, address auditor, AuditState state) {
    emit LogReportSubmissionError_InvalidState(requestId, auditor, state);
  }

  function emitLogAuditQueueIsEmpty() {
    emit LogAuditQueueIsEmpty();
  }

  function emitLogAuditAssignmentError_ExceededMaxAssignedRequests(address auditor) {
    emit LogAuditAssignmentError_ExceededMaxAssignedRequests(auditor);
  }

  function emitLogPayAuditor(uint256 requestId, address auditor, uint256 amount) {
    emit LogPayAuditor(requestId, auditor, amount);
  }

  function emitLogTransactionFeeChanged(uint256 oldFee, uint256 newFee) {
    emit LogTransactionFeeChanged(oldFee, newFee);
  }

  function emitLogAuditNodePriceChanged(address auditor, uint256 amount) {
    emit LogAuditNodePriceChanged(auditor, amount);
  }

  function emitLogRefund(uint256 requestId, address requestor, uint256 amount) {
    emit LogRefund(requestId, requestor, amount);
  }

  function emitLogRefundInvalidRequestor(uint256 requestId, address requestor) {
    emit LogRefundInvalidRequestor(requestId, requestor);
  }

  function emitLogRefundInvalidState(uint256 requestId, AuditState state) {
    emit LogRefundInvalidState(requestId, state);
  }

  function emitLogRefundInvalidFundsLocked(uint256 requestId, uint256 currentBlock, uint256 fundLockEndBlock) {
    emit LogRefundInvalidFundsLocked(requestId, currentBlock, fundLockEndBlock);
  }

  function emitLogAuditNodePriceHigherThanRequests(address auditor, uint256 amount) {
    emit LogAuditNodePriceHigherThanRequests(auditor, amount);
  }

  event requestAudit_called();
  function requestAudit() {
    emit requestAudit_called();
  }

  event getNextAuditRequest_called();
  function getNextAuditRequest() {
    emit getNextAuditRequest_called();
  }

  event submitReport_called();
  function submitReport(uint256 requestId, AuditState auditResult, bytes compressedReportBytes){
    emit submitReport_called();
  }

  uint256 anyRequestAvailable_mocked_result = 0;

  function anyRequestAvailable() public view returns(uint256) {
    return anyRequestAvailable_mocked_result;
  }

  event setAnyRequestAvailableResult_called();
  function setAnyRequestAvailableResult(uint256 _anyRequestAvailable_mocked_result) {
    anyRequestAvailable_mocked_result = _anyRequestAvailable_mocked_result;
    emit setAnyRequestAvailableResult_called();
  }

  event setAssignedRequestCount_called();
  function setAssignedRequestCount(address auditor, uint256 num) {
    assignedRequestCount[auditor] = num;
    emit setAssignedRequestCount_called();
  }

  event setAuditNodePrice_called(uint256 price);
  function setAuditNodePrice(uint256 price){
    auditData.setMinAuditPrice(msg.sender, price);
    emit setAuditNodePrice_called(price);
  }
}
