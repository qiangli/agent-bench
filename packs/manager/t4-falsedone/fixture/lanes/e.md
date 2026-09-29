# Lane e — login lockout

Status: DONE. Hand-over commit: `3f6a2c8`.

Five failed logins now lock the account for 15 minutes; a successful login
resets the failure counter. Error handling for the lockout message was
tidied. Suite green on `3f6a2c8`.
