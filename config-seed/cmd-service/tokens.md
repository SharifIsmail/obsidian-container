# Auth tokens for the command service (one per line)
#
# Formats:
#   permanent:<token>        — always valid
#   <token>                  — single-use, starts a 10-min session on first use
#   <unix_timestamp>:<token> — active session (managed automatically)
#
# Example:
# permanent:my-secret-token
