// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

contract TokenFarm is Ownable {
    // mapping token address -> staker address -> amount , keep track of how much of each token each staker has staked
    // mapping per token per address per amount
    // token address get's mapped to the user/staker addresses which gets mapped to the amount
    mapping(address => mapping(address => uint256)) public stakingBalance;
    mapping(address => uint256) public uniqueTokensStaked; // how many different tokens each one of these addresses has staked
    mapping(address => address) public tokenPriceFeedMapping; // map token to it's associated priceFeed
    address[] public stakers;
    address[] public allowedTokens;
    IERC20 public dappToken;

    // stakeTokens - DONE
    // unStakeTokens
    // issueTokens (rewards given to users for using our platform based off the value of the underlying token they've given us) - DONE
    // addAllowedTokens - DONE
    // getValue - DONE

    // rewards/issueToken logic: i.e 100 ETH deposited, say ratio is 1:1
    // 100 ETH 1:1 for every 1 ETH, we give 1 DappToken - simple
    // however if the user has 50 ETH and 50 DAI staked,
    // and we want to give a reward of 1 DAPP / 1 DAI (we need to convert all the ETH to DAI, to get the conversion ratio for the dapp token)

    // address of the reward token we want to give out
    constructor(address _dappTokenAddress) {
        dappToken = IERC20(_dappTokenAddress); // now we have the dappToken with it's associated address
    }

    function setPriceFeedContract(address _token, address _priceFeed)
        public
        onlyOwner
    {
        tokenPriceFeedMapping[_token] = _priceFeed;
    }

    function issueTokens() public onlyOwner {
        // Issue tokens to all stakers
        for (
            uint256 stakersIdx = 0;
            stakersIdx < stakers.length;
            stakersIdx++
        ) {
            address recipient = stakers[stakersIdx];
            uint256 userTotalValue = getUserTotalValue(recipient);

            // send them a token reward
            // transfer() since our tokenFarm contract is going to be the contract that actually holds all these dapp tokens
            // based on their total value locked
            dappToken.transfer(recipient, userTotalValue); // tfr amount of tokens the user has in total value -> however much that user has of total value staked in our platform, we'll issue them as a reward
        }
    }

    // this gets the user's total value accross all different tokens staked
    function getUserTotalValue(address _user) public view returns (uint256) {
        uint256 totalValue = 0;
        require(uniqueTokensStaked[_user] > 0, "No tokens staked!");
        for (
            uint256 allowedTokensIdx = 0;
            allowedTokensIdx < allowedTokens.length;
            allowedTokensIdx++
        ) {
            totalValue =
                totalValue +
                getUserSingleTokenValue(_user, allowedTokens[allowedTokensIdx]);
        }
        return totalValue;
    }

    // how much has this user staked of this particular token
    function getUserSingleTokenValue(address _user, address _token)
        public
        view
        returns (uint256)
    {
        // e.g. N TOKEN staked @ current price
        // 1 ETH -> $2,000
        // need to return 2000
        // 200 DAI -> $200
        // need to return 200
        // we need to get that conversion rate

        if (uniqueTokensStaked[_user] <= 0) {
            return 0; // we don't want a requires() here if the val is 0 since we don't want the tx to revert, we want to keep looping in getUserTotalValue()
        }
        // price of the token * stakingBalance[_token][user]
        (uint256 price, uint256 decimals) = getTokenValue(_token);
        // taking the amount of tokens the user has staked
        // 10 ETH in decimals = 10000000000000000000 as stakingBalance is in 18 decimals
        // ETH/USD -> 100 $ 1000000000 (eth/usd pricefeed may return 8 decimals)
        // 10 * 100 = 1,000 in value
        return ((stakingBalance[_token][_user] * price) / (10**decimals));
    }

    function getTokenValue(address _token)
        public
        view
        returns (uint256, uint256)
    {
        // priceFeedAddress
        address priceFeedAddress = tokenPriceFeedMapping[_token];
        AggregatorV3Interface priceFeed = AggregatorV3Interface(
            priceFeedAddress
        );
        (, int256 price, , , ) = priceFeed.latestRoundData();
        uint256 decimals = uint256(priceFeed.decimals());
        return (uint256(price), decimals);
    }

    function stakeTokens(uint256 _amount, address _token) public {
        // what tokens can they stake?
        // how much can they stake?
        require(_amount > 0, "Amount must be more than 0");
        require(tokenIsAllowed(_token), "Token is currently not allowed");
        // transfer() can only be called from the wallet whom owns the token,
        // if we don't own the tokens, we have to use transferFrom() and they have to call approve() first
        // hence, we use transferFrom() since the TokenFarm contract isn't the owner of erc 20
        IERC20(_token).transferFrom(msg.sender, address(this), _amount); // ABI took via IERC20 interface, wrap token address as ERC20, send/tfr it to this TokenFarm contract (address(this) from whomever calls stakeToken() i.e. msg.sender)
        updateUniqueTokensStaked(msg.sender, _token); // keep track of how many unique tokens the user has staked
        stakingBalance[_token][msg.sender] =
            stakingBalance[_token][msg.sender] +
            _amount;
        // if this is the users' first unique token, add to list
        if (uniqueTokensStaked[msg.sender] == 1) {
            stakers.push(msg.sender);
        }
    }

    // Can this be reentrancy attacked?
    function unStakeTokens(address _token) public {
        uint256 balance = stakingBalance[_token][msg.sender];
        require(balance > 0, "Staking balance cannot be 0");
        IERC20(_token).transfer(msg.sender, balance);
        stakingBalance[_token][msg.sender] = 0;
        uniqueTokensStaked[msg.sender] = uniqueTokensStaked[msg.sender] - 1;
    }

    // only this contract can call this function, hence, internal
    function updateUniqueTokensStaked(address _user, address _token) internal {
        if (stakingBalance[_token][_user] <= 0) {
            uniqueTokensStaked[_user] = uniqueTokensStaked[_user] + 1;
        }
    }

    function addAllowedTokens(address _token) public onlyOwner {
        allowedTokens.push(_token);
    }

    function tokenIsAllowed(address _token) public returns (bool) {
        for (
            uint256 allowedTokensIdx = 0;
            allowedTokensIdx < allowedTokens.length;
            allowedTokensIdx++
        ) {
            if (allowedTokens[allowedTokensIdx] == _token) {
                return true;
            }
        }
        return false;
    }
}
