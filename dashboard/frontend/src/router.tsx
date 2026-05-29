import {
  createRouter,
  createRootRoute,
  createRoute,
  redirect,
  Outlet,
} from "@tanstack/react-router";
import { AppShell } from "@/components/layout/AppShell";
import { LoginPage } from "@/pages/LoginPage";
import { BoardPage } from "@/pages/BoardPage";
import { TaskDetailPage } from "@/pages/TaskDetailPage";
import { HITLQueuePage } from "@/pages/HITLQueuePage";
import { CostPage } from "@/pages/CostPage";
import { HealthPage } from "@/pages/HealthPage";
import { SkillsPage } from "@/pages/SkillsPage";
import { SkillEditorPage } from "@/pages/SkillEditorPage";
import { ReposPage } from "@/pages/ReposPage";
import { LaunchPage } from "@/pages/LaunchPage";
import { ModelsConfigPage } from "@/pages/ModelsConfigPage";
import { ReviewersConfigPage } from "@/pages/ReviewersConfigPage";
import { PoliciesConfigPage } from "@/pages/PoliciesConfigPage";
import { auth as authApi } from "@/lib/api";

// Root route — auth check
const rootRoute = createRootRoute({
  component: Outlet,
});

// Login route (public)
const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  component: LoginPage,
});

// Protected layout route
const layoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: "layout",
  component: AppShell,
  beforeLoad: async () => {
    try {
      const { authenticated } = await authApi.me();
      if (!authenticated) throw redirect({ to: "/login" });
    } catch (e) {
      if (e instanceof Response || (e as { _isRedirect?: boolean })._isRedirect) throw e;
      throw redirect({ to: "/login" });
    }
  },
});

const indexRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: "/",
  beforeLoad: () => { throw redirect({ to: "/board" }); },
});

const boardRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: "/board",
  component: BoardPage,
});

const taskDetailRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: "/tasks/$taskId",
  component: TaskDetailPage,
});

const hitlRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: "/hitl",
  component: HITLQueuePage,
  validateSearch: (search: Record<string, unknown>): { taskId?: string } => ({
    taskId: typeof search.taskId === "string" ? search.taskId : undefined,
  }),
});

const costRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: "/cost",
  component: CostPage,
});

const healthRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: "/health",
  component: HealthPage,
});

const skillsRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: "/skills",
  component: SkillsPage,
});

const skillEditorRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: "/skills/$skillName",
  component: SkillEditorPage,
});

const reposRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: "/repos",
  component: ReposPage,
});

const launchRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: "/launch",
  component: LaunchPage,
});

const modelsConfigRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: "/config/models",
  component: ModelsConfigPage,
});

const reviewersConfigRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: "/config/reviewers",
  component: ReviewersConfigPage,
});

const policiesConfigRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: "/config/policies",
  component: PoliciesConfigPage,
});

const routeTree = rootRoute.addChildren([
  loginRoute,
  layoutRoute.addChildren([
    indexRoute,
    boardRoute,
    taskDetailRoute,
    hitlRoute,
    costRoute,
    healthRoute,
    skillsRoute,
    skillEditorRoute,
    reposRoute,
    launchRoute,
    modelsConfigRoute,
    reviewersConfigRoute,
    policiesConfigRoute,
  ]),
]);

export const router = createRouter({
  routeTree,
  defaultPreload: "intent",
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
