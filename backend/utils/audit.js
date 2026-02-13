function toNullableString(value) {
  if (value === undefined || value === null) return null;
  const text = String(value).trim();
  return text === '' ? null : text;
}

function toNullableInteger(value) {
  if (value === undefined || value === null || value === '') return null;
  const parsed = Number(value);
  return Number.isInteger(parsed) ? parsed : null;
}

function buildAuditActor(headers = {}) {
  return {
    actorUserId: toNullableInteger(headers['x-gateway-user-id']),
    actorUsername: toNullableString(headers['x-gateway-user']) || 'system',
    requestId: toNullableString(headers['x-request-id']),
  };
}

async function recordAudit(client, payload) {
  const {
    entityType,
    entityId,
    action,
    beforeState,
    afterState,
    actorUserId,
    actorUsername,
    requestId,
    sourceService,
  } = payload;

  await client.query(
    `
    INSERT INTO audit_logs (
      entity_type,
      entity_id,
      action,
      before_state,
      after_state,
      actor_user_id,
      actor_username,
      request_id,
      source_service
    )
    VALUES ($1,$2,$3,$4::jsonb,$5::jsonb,$6,$7,$8,$9)
    `,
    [
      entityType,
      String(entityId),
      action,
      beforeState === undefined ? null : JSON.stringify(beforeState),
      afterState === undefined ? null : JSON.stringify(afterState),
      actorUserId ?? null,
      actorUsername ?? null,
      requestId ?? null,
      sourceService ?? null,
    ]
  );
}

module.exports = {
  buildAuditActor,
  recordAudit,
};
