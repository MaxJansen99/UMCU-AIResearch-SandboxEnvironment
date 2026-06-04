1. DynamicFilters.tsx
onClick={onSearch}

2. App.tsx
handleSearch()

3. App.tsx
queryOrthancMetadata(filters)

4. queryClient.ts
queryOrthancMetadata(filters)

5. queryClient.ts
toBackendFilters(filters)

6. queryClient.ts
fetch('/query', {
  method: 'POST',
  body: JSON.stringify({
    filters: [["Modality", "==", "MR"]],
    stats_tags: ["Modality", "StudyDate", "StudyDescription", "SeriesDescription", "BodyPartExamined"]
  })
})

7. server.py
QueryHTTPRequestHandler.do_POST()

8. server.py
query_service.run(payload)

9. query_service.py
QueryService.run(payload)

10. query_service.py
QueryService.query(filters, stats_tags)

11. orthanc_client.py
OrthancClient.find_series(query_body)

12. orthanc_client.py
POST http://orthanc:8042/tools/find

13. query_service.py
QueryService._matches(meta, filters)

14. orthanc_client.py
OrthancClient.get_series(series_id)

15. orthanc_client.py
GET http://orthanc:8042/series/{series_id}

16. orthanc_client.py
OrthancClient.get_instance_tags(instance_id)

17. orthanc_client.py
GET http://orthanc:8042/instances/{instance_id}/tags

18. query_service.py
return {
  stats: ...,
  matched_series: ...
}

19. server.py
self._send_json(response)

20. queryClient.ts
const payload = await response.json()

21. queryClient.ts
toDicomInstance(...)

22. App.tsx
setStats(result.stats)
setAllInstances(result.instances)
setFilteredInstances(result.instances)

23. DynamicTable.tsx / DynamicStatsPanel.tsx
render results