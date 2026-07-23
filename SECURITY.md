# ORE Miner V3 — Security Policy

## Repository Security Rule

ORE Miner V3 must never store or commit sensitive, confidential, or personally identifiable information.

This includes, but is not limited to:

- Passwords
- API keys
- API secrets
- Access tokens
- Authentication credentials
- Private keys
- Solana private keys
- Wallet keypair files
- Wallet seed phrases or recovery phrases
- Personally identifiable information (PII)
- Private email addresses or account information
- SSH private keys
- RPC credentials
- Database credentials
- Encryption keys
- Session tokens
- Any other secret or confidential information

## Secret Management

Secrets required by ORE Miner V3 must be provided through secure external mechanisms such as environment variables.

Local `.env` files may be used for development but must never be committed to Git.

The repository may contain a `.env.example` file containing placeholder variable names only.

Example:

ORE_RPC_URL=YOUR_RPC_URL_HERE
ORE_WALLET_PUBKEY=YOUR_PUBLIC_WALLET_ADDRESS_HERE

Real credentials or secrets must never appear in example configuration files.

## Wallet Security

Wallet private keys and seed phrases must never be stored in this repository.

The Live Miner must never require a seed phrase to be written into source code, configuration files, logs, databases, or command-line history.

Wallet signing should eventually be designed so that private key material is isolated from the strategy, research, observer, simulation, and analytics components.

## Logging

Logs must never contain:

- Private keys
- Seed phrases
- Passwords
- API secrets
- Authentication tokens
- Sensitive environment variables

Logging code must avoid dumping entire environment configurations or credential objects.

## Before Committing

Before committing changes involving configuration, authentication, wallets, RPC providers, or credentials:

1. Review `git status`.
2. Review staged files.
3. Verify no secrets or sensitive data are present.
4. Confirm sensitive files are ignored by `.gitignore`.

Useful commands:

git status

git diff --cached

## If a Secret Is Accidentally Committed

Do not assume deleting the file in a later commit removes the secret from Git history.

Immediately:

1. Revoke or rotate the exposed credential.
2. Stop using the exposed key or token.
3. Remove the secret from the repository and Git history where appropriate.
4. Verify that no other credentials were exposed.

Credential rotation is the first priority because Git history may preserve previously committed data.

## Design Principle

ORE Miner V3 follows this rule:

> Secrets belong outside the repository.

This requirement applies to all current and future ORE Miner V3 components.
