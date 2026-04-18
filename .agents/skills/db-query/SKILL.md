---
name: db-query
description: Query MSSQL database on the VPS to get information about tickets, KB articles, and other data.
---

## When to use
- User asks about data in the database
- Need to check tickets, KB articles, or other records
- Verify data before making changes

## How to connect to MSSQL

Run this command on VPS:
```bash
ssh -i ~/.ssh/baltiyskiy_bereg_new theimage01@111.88.159.116 \
  "docker exec mssql-baltbereg /opt/mssql-tools/bin/sqlcmd \
   -S localhost -U SA -P \"\\" \
   -Q 'YOUR SQL QUERY'"
```

## Key tables

| Table | Columns |
|-------|---------|
| Task | Id, Name, Description, Comment, StatusId, ServiceId, TypeId, CreatedDate |
| KBDocument | Id, Name, Description, IsPublished, Rating |
| TaskExpenses | Id, TaskId, Comments, Minutes, Date |
| TaskFieldValues | Id, TaskId, FieldId, Value |

## Common queries

Count tickets:
```sql
SELECT COUNT(*) FROM service_desk_tdbb.dbo.Task
```

Top 5 recent tickets:
```sql
SELECT TOP 5 Id, Name, CreatedDate FROM service_desk_tdbb.dbo.Task ORDER BY CreatedDate DESC
```

Search tickets by keyword:
```sql
SELECT TOP 10 Name, Description FROM service_desk_tdbb.dbo.Task WHERE Name LIKE '%keyword%'
```

KB articles:
```sql
SELECT TOP 10 Name, IsPublished FROM service_desk_tdbb.dbo.KBDocument
```

## Always
- Use TOP/LIMIT to limit results
- Close connection after use (handled by docker exec)
