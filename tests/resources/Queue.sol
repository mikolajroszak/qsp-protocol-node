pragma solidity 0.4.18;

////////////////////////////////////////////////////////////
// Based on: https://github.com/chriseth/solidity-examples/blob/master/queue.sol
////////////////////////////////////////////////////////////
contract Uint256Queue {
  uint256[] private data;
  uint private front;
  uint private back;
  
  event LogQueueIsEmptyError();
  event LogQueueIsFullError(uint capacity, uint256 item);
  event LogInvalidItem(uint256 item);

  enum PopResult {
    Success,
    QueueIsEmpty
  }
  
  enum PushResult {
    Success,
    QueueIsFull
  }
  
  function Uint256Queue(uint capacity) public { 
    data.length = capacity;
  }

  function length() constant public returns (uint) {
    return (data.length + back - front) % data.length;
  }

  function capacity() constant public returns (uint) {
    return data.length;
  }

  function push(uint256 item) public returns (PushResult) {
    if ((back + 1) % data.length == front) {
      LogQueueIsFullError(capacity(), item);
      return PushResult.QueueIsFull;
    }
    data[back] = item;
    back = (back + 1) % data.length;
    return PushResult.Success;
  }

  function pop() public returns (PopResult result, uint256 item) {
    if (back == front) {
      LogQueueIsEmptyError();
      result = PopResult.QueueIsEmpty;
      return;
    }

    item = data[front];
    delete(data[front]);
    front = (front + 1) % data.length;
    result = PopResult.Success;
  }
}