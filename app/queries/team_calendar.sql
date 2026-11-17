-- Weekends and holidays are left out. Parameters manager_id, range_start, range_end.


SELECT d::date AS day,
       e.id    AS employee_id,
       e.name  AS employee_name,
       lt.name AS leave_type
FROM generate_series(
         CAST(:range_start AS date),
         CAST(:range_end AS date),
         interval '1 day'
     ) AS d
JOIN leave_requests lr
  ON d::date BETWEEN lr.start_date AND lr.end_date
 AND lr.status = 'approved'
JOIN employees e
  ON e.id = lr.employee_id
 AND e.manager_id = :manager_id
JOIN leave_types lt ON lt.id = lr.leave_type_id
WHERE EXTRACT(ISODOW FROM d) < 6
  AND NOT EXISTS (
        SELECT 1 FROM holidays h WHERE h.holiday_date = d::date
  )
ORDER BY day, e.name;