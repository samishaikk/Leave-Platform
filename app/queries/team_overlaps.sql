-- Pairs of teammates whose open (pending or approved) leave overlaps.
-- Parameter manager_id.


SELECT a.id   AS request_a,
       ea.name AS employee_a,
       b.id   AS request_b,
       eb.name AS employee_b,
       GREATEST(a.start_date, b.start_date) AS overlap_start,
       LEAST(a.end_date, b.end_date)        AS overlap_end
FROM leave_requests a
JOIN leave_requests b
  ON a.id < b.id
 AND a.employee_id <> b.employee_id
 AND a.start_date <= b.end_date
 AND b.start_date <= a.end_date
JOIN employees ea ON ea.id = a.employee_id
JOIN employees eb ON eb.id = b.employee_id
WHERE ea.manager_id = :manager_id
  AND eb.manager_id = :manager_id
  AND a.status IN ('pending', 'approved')
  AND b.status IN ('pending', 'approved')
ORDER BY overlap_start, a.id, b.id;