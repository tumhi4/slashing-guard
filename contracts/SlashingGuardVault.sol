// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SlashingGuardVault
 * @notice Underwriting reserve and reimbursement vault for Ethereum validator slashing insurance.
 * Coordinates collateral custody, premium deposits, and automated parametric claim payouts
 * authorized by the GenLayer SlashingGuardCourt Intelligent Contract.
 */
contract SlashingGuardVault {
    address public owner;
    address public authorizedRelay;

    uint256 public totalReserves;
    uint256 public totalClaimsPaid;

    mapping(bytes32 => bool) public settledClaims;
    mapping(address => uint256) public stakerPremiums;

    event PremiumDeposited(address indexed staker, uint256 amount);
    event ClaimPaid(bytes32 indexed policyId, address indexed staker, uint256 amount);
    event ReservesReplenished(uint256 amount);

    error Unauthorized();
    error AlreadySettled();
    error InsufficientReserves();
    error InvalidAddress();
    error InvalidAmount();

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    modifier onlyRelay() {
        if (msg.sender != authorizedRelay && msg.sender != owner) revert Unauthorized();
        _;
    }

    constructor(address _relay) {
        if (_relay == address(0)) revert InvalidAddress();
        owner = msg.sender;
        authorizedRelay = _relay;
    }

    /**
     * @notice Replenishes underwriting liquidity pool.
     */
    function replenishReserves() external payable onlyOwner {
        totalReserves += msg.value;
        emit ReservesReplenished(msg.value);
    }

    /**
     * @notice Deposits annual premium for a validator insurance policy.
     */
    function depositPremium() external payable {
        if (msg.value == 0) revert InvalidAmount();
        stakerPremiums[msg.sender] += msg.value;
        totalReserves += msg.value;
        emit PremiumDeposited(msg.sender, msg.value);
    }

    /**
     * @notice Disburses verified slashing claim to the insured staker.
     * Callable only by the authorized GenLayer settlement relay upon verified consensus approval.
     */
    function executeSlashingPayout(
        bytes32 policyId,
        address payable staker,
        uint256 amount
    ) external onlyRelay returns (bool) {
        if (staker == address(0)) revert InvalidAddress();
        if (amount == 0) revert InvalidAmount();
        if (settledClaims[policyId]) revert AlreadySettled();
        if (totalReserves < amount) revert InsufficientReserves();

        settledClaims[policyId] = true;
        totalReserves -= amount;
        totalClaimsPaid += amount;

        (bool success, ) = staker.call{value: amount}("");
        require(success, "Transfer failed");

        emit ClaimPaid(policyId, staker, amount);
        return true;
    }

    /**
     * @notice Updates the authorized settlement relay address.
     */
    function setAuthorizedRelay(address _newRelay) external onlyOwner {
        if (_newRelay == address(0)) revert InvalidAddress();
        authorizedRelay = _newRelay;
    }

    receive() external payable {
        totalReserves += msg.value;
    }
}
