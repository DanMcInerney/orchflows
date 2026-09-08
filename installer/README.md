# Publication and recovery

An install serializes concurrent installers with `installer.locking`, stages
library, scripts and browser assets, and retains their prior bytes until
publication succeeds. The private runtime is rechecked under that lock;
a healthy runtime is reused, while creation or repair uses its staged
replacement and recovery path.

Upgrades do not read, migrate or require closing ticket history. Ticket
commands do not participate in installation exclusion. Ordinary shared-runtime
upgrades do not promise continued compatibility for already-running commands.

The flat script directory may contain operator-authored helpers. A newly
shipped script with differing bytes at an unowned destination refuses with
the exact conflicting path, leaving the helper and receipt intact. Resolve
that collision explicitly before retrying; noncolliding helpers are preserved.

On a failed rollback, the error names `.install-transaction-<id>` and its
`recovery.json`. Keep that directory: it contains the complete prior
payload directories and copies of changed external surfaces. Further
installation refuses while this recovery map remains. With clients stopped,
restore the recorded backups to the recorded live paths (parking any new
partial payload first), restore the recorded surface copies, and verify
the old receipt and entrypoints. Only then archive the transaction directory
outside the installation home and retry. Never delete the sole backup to
make a retry pass.
