// Minimal toast state hook (shadcn pattern)
import * as React from "react";
import type { ToastProps } from "@/components/ui/toast";

const TOAST_LIMIT = 5;
const TOAST_REMOVE_DELAY = 4000;

type ToastItem = ToastProps & {
  id: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactElement;
};

type State = { toasts: ToastItem[] };

let count = 0;
function genId() {
  count = (count + 1) % Number.MAX_SAFE_INTEGER;
  return String(count);
}

const listeners: Array<(state: State) => void> = [];
let memState: State = { toasts: [] };

function dispatch(action: { type: "ADD" | "DISMISS" | "REMOVE"; toast?: ToastItem; toastId?: string }) {
  switch (action.type) {
    case "ADD":
      memState = { toasts: [action.toast!, ...memState.toasts].slice(0, TOAST_LIMIT) };
      break;
    case "DISMISS":
      memState = {
        toasts: memState.toasts.map((t) =>
          t.id === action.toastId || action.toastId === undefined
            ? { ...t, open: false }
            : t,
        ),
      };
      break;
    case "REMOVE":
      memState = { toasts: memState.toasts.filter((t) => t.id !== action.toastId) };
      break;
  }
  listeners.forEach((l) => l(memState));
}

export function toast(props: Omit<ToastItem, "id">) {
  const id = genId();
  const dismiss = () => dispatch({ type: "DISMISS", toastId: id });
  dispatch({
    type: "ADD",
    toast: {
      ...props,
      id,
      open: true,
      onOpenChange: (open) => {
        if (!open) {
          dismiss();
          setTimeout(() => dispatch({ type: "REMOVE", toastId: id }), TOAST_REMOVE_DELAY);
        }
      },
    },
  });
  return { id, dismiss };
}

export function useToast() {
  const [state, setState] = React.useState<State>(memState);
  React.useEffect(() => {
    listeners.push(setState);
    return () => {
      const idx = listeners.indexOf(setState);
      if (idx > -1) listeners.splice(idx, 1);
    };
  }, []);
  return { ...state, toast, dismiss: (id?: string) => dispatch({ type: "DISMISS", toastId: id }) };
}
