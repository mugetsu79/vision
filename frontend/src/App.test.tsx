import { render, screen } from "@testing-library/react";
import App from "./App";

describe("App", () => {
  it("renders the Prompt 1 empty shell", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: /traffic monitor v4/i })).toBeInTheDocument();
    expect(
      screen.getByText(/prompt 1 scaffold ready for backend, frontend, and infra/i),
    ).toBeInTheDocument();
  });
});
