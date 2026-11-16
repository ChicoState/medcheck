# ADR 001: Account-owned weekly schedule

Status: Accepted

Store one schedule per user and individual doses as related rows. Add an additive migration after the existing medication and saved-label migration so upgraded databases retain those records. The session-authenticated API seeds example doses on first access, then returns persisted rows. Scheduling a saved medicine links doses to that account's saved record and replaces the examples. Updates and removal check ownership and replace only that medicine's entries. The browser does not store a separate copy.
