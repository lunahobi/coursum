import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});

if (!URL.createObjectURL) {
  URL.createObjectURL = (() => "blob:preview") as typeof URL.createObjectURL;
}

if (!URL.revokeObjectURL) {
  URL.revokeObjectURL = (() => undefined) as typeof URL.revokeObjectURL;
}
