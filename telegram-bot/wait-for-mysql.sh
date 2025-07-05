#!/bin/bash
# Wait for MySQL/MariaDB to be ready

set -e

host="$1"
shift
cmd="$@"

until mysql -h "$host" -u root -p"${MYSQL_ROOT_PASSWORD:-rootpassword}" -e 'SELECT 1'; do
  >&2 echo "MySQL is unavailable - sleeping"
  sleep 1
done

>&2 echo "MySQL is up - executing command"
exec $cmd 