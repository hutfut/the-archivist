import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { ErrorBoundary } from "../ErrorBoundary";

function ThrowingChild({ error }: { error?: Error }) {
  if (error) throw error;
  return <p>All good</p>;
}

function renderWithRouter(ui: React.ReactElement) {
  return render(ui, { wrapper: ({ children }) => <MemoryRouter>{children}</MemoryRouter> });
}

describe("ErrorBoundary", () => {
  it("renders children when no error occurs", () => {
    renderWithRouter(
      <ErrorBoundary>
        <p>Content</p>
      </ErrorBoundary>,
    );

    expect(screen.getByText("Content")).toBeInTheDocument();
  });

  it("shows fallback UI when a child throws", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});

    renderWithRouter(
      <ErrorBoundary>
        <ThrowingChild error={new Error("Boom")} />
      </ErrorBoundary>,
    );

    expect(screen.getByText(/shrouded in darkness/)).toBeInTheDocument();
    expect(screen.getByText("Something went wrong rendering this page.")).toBeInTheDocument();
    expect(screen.getByText("Boom")).toBeInTheDocument();
  });

  it("re-renders children after clicking Try Again", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const user = userEvent.setup();

    let shouldThrow = true;
    function MaybeThrow() {
      if (shouldThrow) throw new Error("Fail");
      return <p>Recovered</p>;
    }

    renderWithRouter(
      <ErrorBoundary>
        <MaybeThrow />
      </ErrorBoundary>,
    );

    expect(screen.getByText(/shrouded in darkness/)).toBeInTheDocument();

    shouldThrow = false;
    await user.click(screen.getByRole("button", { name: "Try Again" }));

    expect(screen.getByText("Recovered")).toBeInTheDocument();
  });

  it("has a Return Home link pointing to /", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});

    renderWithRouter(
      <ErrorBoundary>
        <ThrowingChild error={new Error("Oops")} />
      </ErrorBoundary>,
    );

    const link = screen.getByRole("link", { name: "Return Home" });
    expect(link).toHaveAttribute("href", "/");
  });
});
