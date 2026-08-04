import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it } from "vitest"
import {
  createMockServices,
  type MockServiceBundle,
} from "../../services/mock/createMockServices"
import { RepositoryPage } from "./RepositoryPage"

describe("RepositoryPage", () => {
  let bundle: MockServiceBundle

  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    bundle = createMockServices()
    bundle.control.setLatency(0)
  })

  it("indexes, asks, vector-indexes, and vector-searches repositories", async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <RepositoryPage repositoryService={bundle.services.repositories} />
      </MemoryRouter>,
    )

    await user.type(
      screen.getByLabelText("Absolute path"),
      "C:\\Users\\naran\\sample-repo",
    )
    await user.click(
      screen.getByRole("button", { name: "Create keyword index" }),
    )

    expect(await screen.findByText("sample-repo")).toBeInTheDocument()
    expect(screen.getByText("12 files, 36 chunks")).toBeInTheDocument()

    await user.type(screen.getByLabelText("Question"), "Where is routing?")
    await user.click(screen.getByRole("button", { name: "Ask repository" }))
    expect(
      await screen.findByText(/Grounded mock answer for sample-repo/),
    ).toBeInTheDocument()
    expect(screen.getByText("sample-repo/src/app.py")).toBeInTheDocument()

    await user.click(
      screen.getByRole("button", { name: "Create vector index" }),
    )
    expect(await screen.findByText(/36 embedded chunks/)).toBeInTheDocument()

    await user.type(screen.getByLabelText("Vector query"), "banana")
    await user.click(screen.getByRole("button", { name: "Search vectors" }))
    expect(await screen.findByText("src/app.py")).toBeInTheDocument()
    expect(
      screen.getByText("class BananaRouter handles repository routing."),
    ).toBeInTheDocument()
    expect(screen.getByText(/Score 0.870/)).toBeInTheDocument()
  }, 15_000)
})
