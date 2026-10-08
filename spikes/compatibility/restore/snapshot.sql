SELECT json_build_object(
    'tenants', (SELECT json_agg(t ORDER BY tenant_id) FROM tenants t),
    'permits', (SELECT json_agg(p ORDER BY tenant_id, permit_id) FROM permits p),
    'attachments', (SELECT json_agg(a ORDER BY tenant_id, attachment_id) FROM attachments a),
    'write_markers', (SELECT json_agg(w ORDER BY marker) FROM write_markers w)
);
