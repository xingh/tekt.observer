import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { vi } from "vitest";
import { App } from "./App";

vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

test("shows a useful starter inbox when the API is offline", async () => {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><App /></QueryClientProvider>);
  expect(screen.getByRole("heading", { name: "Your inbox" })).toBeInTheDocument();
  expect(await screen.findByText("Senior AI Platform Engineer")).toBeInTheDocument();
  expect(screen.getAllByText("AI Markets & Regulation").length).toBeGreaterThan(0);
  expect(screen.getByText(/Highest-priority items appear first/)).toBeInTheDocument();
  expect(screen.getByLabelText("Save Senior AI Platform Engineer")).toBeInTheDocument();
  expect(screen.getByLabelText("Dismiss Senior AI Platform Engineer")).toBeInTheDocument();
});
