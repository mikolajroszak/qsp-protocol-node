/***************************************************************************************************
 *                                                                                                 *
 * (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at   *
 * <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>.                                 *
 *                                                                                                 *
 **************************************************************************************************/

pragma solidity 0.4.2;

contract SendBalance {
  mapping (address => uint) userBalances;
  bool withdrawn = false;

  function getBalance(address u) constant returns (uint) {
    return userBalances[u];
  }

  function addToBalance() {
    userBalances[msg.sender] += msg.value;
  }

  function withdrawBalance() {
    if (!(msg.sender.call.value(userBalances[msg.sender])())) {
      throw;
    }

    userBalances[msg.sender] = 0;
  }
}
