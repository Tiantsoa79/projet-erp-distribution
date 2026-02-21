function resolveDatabaseErrorStatus(error) {
  if (error && (error.code === '23505' || error.code === '23503')) {
    return 409;
  }
  return 500;
}

function resolveHttpStatus(error) {
  if (error && Number.isInteger(error.status) && error.status >= 400 && error.status <= 599) {
    return error.status;
  }
  return resolveDatabaseErrorStatus(error);
}

function sendServiceError(res, serviceLabel, error) {
  const status = resolveHttpStatus(error);
  res.status(status).json({
    message: `${serviceLabel} service error`,
    detail: error.message,
  });
}

module.exports = {
  resolveDatabaseErrorStatus,
  resolveHttpStatus,
  sendServiceError,
};
