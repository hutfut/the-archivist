export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function parseErrorResponse(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    // Response wasn't JSON or didn't have a detail field
  }
  return response.statusText || `Request failed (${response.status})`;
}

export async function throwIfNotOk(response: Response): Promise<void> {
  if (!response.ok) {
    const message = await parseErrorResponse(response);
    throw new ApiError(response.status, message);
  }
}
