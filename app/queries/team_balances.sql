
WITH team AS (
    SELECT id, name
    FROM employees
    WHERE manager_id = :manager_id
),
usage AS (
    SELECT employee_id,
           leave_type_id,
           SUM(days) FILTER (WHERE status = 'approved') AS approved_days,
           SUM(days) FILTER (WHERE status = 'pending')  AS pending_days
    FROM leave_requests
    WHERE EXTRACT(YEAR FROM start_date) = :year
      AND status IN ('approved', 'pending')
    GROUP BY employee_id, leave_type_id
)
SELECT t.id   AS employee_id,
       t.name AS employee_name,
       lt.name AS leave_type,
       lt.annual_quota,
       COALESCE(u.approved_days, 0) AS approved_days,
       COALESCE(u.pending_days, 0)  AS pending_days,
       CASE
           WHEN lt.annual_quota IS NULL THEN NULL
           ELSE lt.annual_quota - COALESCE(u.approved_days, 0) - COALESCE(u.pending_days, 0)
       END AS remaining_days
FROM team t
CROSS JOIN leave_types lt
LEFT JOIN usage u
       ON u.employee_id = t.id
      AND u.leave_type_id = lt.id
ORDER BY t.name, lt.id;