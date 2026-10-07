import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { NurseCitationList } from "../NurseCitationList";

describe("NurseCitationList", () => {
  it("links each saved citation code to its retrieved-source page", () => {
    render(
      <NurseCitationList
        caseId="case/01"
        citations={[
          {
            code: "p5doc_d63c62370ba3c9b87de2",
            title: "Is the Patient in Severe Pain or Distress?",
            excerpt: "Retrieved passage",
            source_uri: null,
            section: "Decision Point B",
            version: "v5",
            content_hash: "hash-1",
          },
        ]}
      />,
    );

    expect(
      screen.getByRole("link", {
        name: "Xem nguồn tham chiếu p5doc_d63c62370ba3c9b87de2",
      }),
    ).toHaveAttribute(
      "href",
      "/clinical/cases/case%2F01/sources/p5doc_d63c62370ba3c9b87de2",
    );
  });
});
