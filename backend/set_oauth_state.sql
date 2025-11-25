UPDATE ticketing_tool_connections 
SET meta_data = jsonb_set(meta_data::jsonb, '{oauth_state}', '"7:postman-test-2024"')::text 
WHERE id = 7;



