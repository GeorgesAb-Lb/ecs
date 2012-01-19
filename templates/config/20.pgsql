### backupninja PostgreSQL config file ###

# vsname = <vserver> (no default)
# what vserver to operate on, only used if vserver = yes in /etc/backupninja.conf
# if you do not specify a vsname the host will be operated on
# Note: if operating on a vserver,  will be prepended to backupdir.
# backupdir = <dir> (default: /var/backups/postgres)
# where to dump the backups
backupdir = /var/backups/postgres

# databases = < all | db1 db2 db3 > (default = all)
# which databases to backup. should either be the word 'all' or a 
# space separated list of database names.
# Note: when using 'all', pg_dumpall is used instead of pg_dump, which means
# that cluster-wide data (such as users and groups) are saved.
databases = all

# compress = < yes | no > (default = yes)
# if yes, compress the pg_dump/pg_dumpall output. 
compress = yes

### You can also set the following variables in backupninja.conf:
# PGSQLDUMP: pg_dump path (default: /usr/bin/pg_dump)
# PGSQLDUMPALL: pg_dumpall path (default: /usr/bin/pg_dumpall)
# PGSQLUSER: user running PostgreSQL (default: postgres)
