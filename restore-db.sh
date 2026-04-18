#!/usr/bin/env bash
# Восстанавливает базу данных из backup при первом запуске
set -euo pipefail

BACKUP_PATH="/var/opt/mssql/backup/cleaned.bak"
DB_NAME="service_desk_tdbb"
SA_PASSWORD="${MSSQL_SA_PASSWORD:?}"
SQLCMD="/opt/mssql-tools/bin/sqlcmd"

echo "Waiting for SQL Server to start..."
for i in $(seq 1 60); do
    if $SQLCMD -S localhost -U SA -P "$SA_PASSWORD" -Q "SELECT 1" -b -o /dev/null 2>/dev/null; then
        echo "SQL Server is ready"
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo "ERROR: SQL Server did not start in time"
        exit 1
    fi
    sleep 2
done

if [ ! -r "$BACKUP_PATH" ]; then
    echo "ERROR: Backup file $BACKUP_PATH is not readable"
    exit 1
fi

# Check if DB already exists
EXISTS=$($SQLCMD -S localhost -U SA -P "$SA_PASSWORD" -Q "SET NOCOUNT ON; SELECT COUNT(*) FROM sys.databases WHERE name='$DB_NAME'" -h -1 -b 2>/dev/null | tr -d '[:space:]')

if [ "$EXISTS" = "0" ]; then
    echo "Restoring $DB_NAME from backup..."
    FILELIST=$($SQLCMD -S localhost -U SA -P "$SA_PASSWORD" -Q "RESTORE FILELISTONLY FROM DISK = '$BACKUP_PATH'" -h -1 -W -s "|" -b)
    if [ -z "$FILELIST" ]; then
        echo "ERROR: Could not read backup file list"
        exit 1
    fi

    MOVE_CLAUSES=""
    while IFS='|' read -r LOGICAL_NAME PHYSICAL_NAME _; do
        if [ -z "$LOGICAL_NAME" ] || [ -z "$PHYSICAL_NAME" ]; then
            continue
        fi
        if [ -n "$MOVE_CLAUSES" ]; then
            MOVE_CLAUSES="$MOVE_CLAUSES,"
        fi
        MOVE_CLAUSES="$MOVE_CLAUSES\n             MOVE '$LOGICAL_NAME' TO '$PHYSICAL_NAME'"
    done <<EOF
$FILELIST
EOF

    $SQLCMD -S localhost -U SA -P "$SA_PASSWORD" -Q "
        RESTORE DATABASE [$DB_NAME]
        FROM DISK = '$BACKUP_PATH'
        WITH$(printf '%b' "$MOVE_CLAUSES"),
             REPLACE
    " -b
    echo "Database restored successfully"
else
    echo "Database $DB_NAME already exists, skipping restore"
fi
