WITH team AS (
    SELECT id, name
    FROM employees
    WHERE manager_id = :manager_id
),
totals AS (
    SELECT a.employee_id,
           COUNT(*) AS days_present,
           SUM(EXTRACT(EPOCH FROM (a.check_out - a.check_in)) / 3600.0) AS total_hours
    FROM attendance a
    WHERE a.work_date >= :first_day
      AND a.work_date <  :next_month
      AND a.check_out IS NOT NULL
    GROUP BY a.employee_id
)
SELECT t.id   AS employee_id,
       t.name AS employee_name,
       COALESCE(x.days_present, 0) AS days_present,
       ROUND(COALESCE(x.total_hours, 0)::numeric, 2) AS total_hours,
       ROUND((COALESCE(x.total_hours, 0) / NULLIF(x.days_present, 0))::numeric, 2)
           AS avg_hours_per_day,
       RANK() OVER (ORDER BY COALESCE(x.total_hours, 0) DESC) AS hours_rank
FROM team t
LEFT JOIN totals x ON x.employee_id = t.id
ORDER BY hours_rank, t.name;