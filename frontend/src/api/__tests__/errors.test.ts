import { describe, it, expect, vi } from "vitest";
import { ApiError, parseErrorResponse, throwIfNotOk } from "../errors";

describe("ApiError", () => {
  it("has the correct name", () => {
    const err = new ApiError(404, "Not found");
    expect(err.name).toBe("ApiError");
  });

  it("has the correct status and message", () => {
    const err = new ApiError(500, "Server error");
    expect(err.status).toBe(500);
    expect(err.message).toBe("Server error");
  });

  it("is an instance of Error", () => {
    const err = new ApiError(400, "Bad request");
    expect(err).toBeInstanceOf(Error);
  });
});

describe("parseErrorResponse", () => {
  it("extracts detail from JSON response", async () => {
    const response = new Response(JSON.stringify({ detail: "Not authorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
    const message = await parseErrorResponse(response);
    expect(message).toBe("Not authorized");
  });

  it("falls back to statusText for non-JSON response", async () => {
    const response = new Response("plain text", {
      status: 500,
      statusText: "Internal Server Error",
    });
    const message = await parseErrorResponse(response);
    expect(message).toBe("Internal Server Error");
  });

  it("falls back when JSON has no detail field", async () => {
    const response = new Response(JSON.stringify({ error: "something" }), {
      status: 400,
      statusText: "Bad Request",
      headers: { "Content-Type": "application/json" },
    });
    const message = await parseErrorResponse(response);
    expect(message).toBe("Bad Request");
  });

  it("falls back when detail is not a string", async () => {
    const response = new Response(JSON.stringify({ detail: 123 }), {
      status: 422,
      statusText: "Unprocessable Entity",
      headers: { "Content-Type": "application/json" },
    });
    const message = await parseErrorResponse(response);
    expect(message).toBe("Unprocessable Entity");
  });

  it("falls back to generic message when no statusText", async () => {
    const response = {
      json: vi.fn().mockRejectedValue(new Error("parse error")),
      statusText: "",
      status: 418,
    } as unknown as Response;
    const message = await parseErrorResponse(response);
    expect(message).toBe("Request failed (418)");
  });
});

describe("throwIfNotOk", () => {
  it("does not throw for ok response", async () => {
    const response = new Response("ok", { status: 200 });
    await expect(throwIfNotOk(response)).resolves.toBeUndefined();
  });

  it("throws ApiError for non-ok response", async () => {
    const response = new Response(JSON.stringify({ detail: "Not found" }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });
    await expect(throwIfNotOk(response)).rejects.toThrow(ApiError);
  });

  it("throws ApiError with correct status", async () => {
    const response = new Response(JSON.stringify({ detail: "Forbidden" }), {
      status: 403,
      headers: { "Content-Type": "application/json" },
    });
    try {
      await throwIfNotOk(response);
      expect.fail("Should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(403);
      expect((err as ApiError).message).toBe("Forbidden");
    }
  });
});
