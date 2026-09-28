export type SubmissionFormDraft = {
  values: Record<string, string[]>;
  checkedValues: Record<string, string[]>;
};

type FormControl = {
  name: string;
  value: string;
  type?: string;
  checked?: boolean;
};

export function captureSubmissionDraft(form: Pick<HTMLFormElement, "elements">): SubmissionFormDraft {
  const draft: SubmissionFormDraft = { values: {}, checkedValues: {} };

  for (const element of Array.from(form.elements)) {
    const control = element as unknown as FormControl;
    if (!control.name) continue;

    if (control.type === "checkbox" || control.type === "radio") {
      if (control.checked) {
        (draft.checkedValues[control.name] ??= []).push(control.value);
      }
      continue;
    }
    (draft.values[control.name] ??= []).push(control.value);
  }

  return draft;
}

export function restoreSubmissionDraft(
  form: Pick<HTMLFormElement, "elements">,
  draft: SubmissionFormDraft,
) {
  const valueIndexes = new Map<string, number>();

  for (const element of Array.from(form.elements)) {
    const control = element as unknown as FormControl;
    if (!control.name) continue;

    if (control.type === "checkbox" || control.type === "radio") {
      control.checked = (draft.checkedValues[control.name] ?? []).includes(control.value);
      continue;
    }

    const index = valueIndexes.get(control.name) ?? 0;
    control.value = draft.values[control.name]?.[index] ?? "";
    valueIndexes.set(control.name, index + 1);
  }
}
