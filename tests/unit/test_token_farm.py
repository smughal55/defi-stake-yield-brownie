from brownie import network, exceptions
from scripts.helpful_scripts import (
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    get_account,
    get_contract,
    INITIAL_PRICE_FEED_VALUE,
    DECIMALS,
)
import pytest
from scripts.deploy import deploy_token_farm_and_dapp_token
from web3 import Web3


def test_add_allowed_tokens():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")
    account = get_account()
    non_owner = get_account(index=1)
    token_farm, dapp_token = deploy_token_farm_and_dapp_token()
    # Act
    token_farm.addAllowedTokens(dapp_token.address, {"from": account})
    # Assert
    assert token_farm.allowedTokens(0) == dapp_token.address
    with pytest.raises(exceptions.VirtualMachineError):
        token_farm.addAllowedTokens(dapp_token.address, {"from": non_owner})


def test_set_price_feed_contract():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing!")
    account = get_account()
    non_owner = get_account(
        index=1
    )  # check some onlyOwner functions with this non_owner
    token_farm, dapp_token = deploy_token_farm_and_dapp_token()
    # Act
    price_feed_address = get_contract("eth_usd_price_feed")
    token_farm.setPriceFeedContract(
        dapp_token.address, price_feed_address, {"from": account}
    )
    # Assert
    assert token_farm.tokenPriceFeedMapping(dapp_token.address) == price_feed_address
    with pytest.raises(exceptions.VirtualMachineError):
        token_farm.setPriceFeedContract(
            dapp_token.address, price_feed_address, {"from": non_owner}
        )


def test_stake_tokens(amount_staked):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing!")
    account = get_account()
    token_farm, dapp_token = deploy_token_farm_and_dapp_token()
    # Act
    dapp_token.approve(token_farm.address, amount_staked, {"from": account})
    token_farm.stakeTokens(amount_staked, dapp_token.address, {"from": account})
    # Assert
    print(
        f"Staking balance is: {token_farm.stakingBalance(dapp_token.address, account.address)}"
    )
    assert (
        token_farm.stakingBalance(dapp_token.address, account.address) == amount_staked
    )
    assert token_farm.uniqueTokensStaked(account.address) == 1
    assert token_farm.stakers(0) == account.address
    return token_farm, dapp_token


def test_stake_unapproved_tokens(random_erc20, amount_staked):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")
    account = get_account()
    token_farm, dapp_token = deploy_token_farm_and_dapp_token()
    # Act
    random_erc20.approve(token_farm.address, amount_staked, {"from": account})
    # Assert
    with pytest.raises(exceptions.VirtualMachineError):
        token_farm.stakeTokens(amount_staked, random_erc20.address, {"from": account})


def test_unstake_tokens(amount_staked):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")
    account = get_account()
    token_farm, dapp_token = test_stake_tokens(amount_staked)
    # Act
    token_farm.unStakeTokens(dapp_token.address, {"from": account})
    # Assert
    assert dapp_token.balanceOf(account.address) == Web3.toWei(100, "ether")
    assert token_farm.stakingBalance(dapp_token.address, account.address) == 0
    assert token_farm.uniqueTokensStaked(account.address) == 0


def test_get_user_total_balance_with_different_tokens_and_amounts(
    amount_staked, random_erc20
):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")
    account = get_account()
    token_farm, dapp_token = test_stake_tokens(amount_staked)
    # Act
    token_farm.addAllowedTokens(random_erc20.address, {"from": account})
    # The random_erc20 is going to represent DAI
    # Since the other mocks auto deploy
    token_farm.setPriceFeedContract(
        random_erc20.address, get_contract("eth_usd_price_feed"), {"from": account}
    )
    random_erc20_stake_amount = amount_staked * 2
    random_erc20.approve(
        token_farm.address, random_erc20_stake_amount, {"from": account}
    )
    token_farm.stakeTokens(
        random_erc20_stake_amount, random_erc20.address, {"from": account}
    )
    # Act
    total_eth_balance = token_farm.getUserTotalValue(account.address)
    assert total_eth_balance == INITIAL_PRICE_FEED_VALUE * 3
    # Improve by adding different mock price feed default values


def test_get_token_value():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")
    token_farm, dapp_token = deploy_token_farm_and_dapp_token()
    # Act / Assert
    assert token_farm.getTokenValue(dapp_token.address) == (
        INITIAL_PRICE_FEED_VALUE,
        DECIMALS,
    )


def test_get_user_single_token_value(amount_staked):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")
    account = get_account()
    token_farm, dapp_token = deploy_token_farm_and_dapp_token()
    # Act
    dapp_token.approve(token_farm.address, amount_staked, {"from": account})
    token_farm.stakeTokens(amount_staked, dapp_token.address, {"from": account})
    # Assert
    eth_balance_token = token_farm.getUserSingleTokenValue(
        account.address, dapp_token.address
    )
    assert eth_balance_token == Web3.toWei(2000, "ether")


def test_issue_tokens(amount_staked):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing!")
    account = get_account()
    token_farm, dapp_token = test_stake_tokens(amount_staked)
    starting_balance = dapp_token.balanceOf(account.address)
    # Act
    token_farm.issueTokens({"from": account})
    # Assert
    # we are staking 1 dapp_token == in price to 1 ETH
    # so, we should get 2,000 dapp tokens in reward
    # since the price of eth is $2,000 (INITIAL_PRICE_FEED_VALUE -> MockV3Aggregator)
    assert (
        dapp_token.balanceOf(account.address)
        == starting_balance + INITIAL_PRICE_FEED_VALUE
    )
