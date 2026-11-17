import { Scene, DependencyGraph, SceneStatus } from "./video-types";

/** Topological sort using Kahn's algorithm. Returns ordered scene IDs. */
export function buildExecutionOrder(scenes: Scene[]): string[] {
  const idToScene = new Map(scenes.map((s) => [s.id, s]));
  const inDegree = new Map<string, number>();
  const adjList = new Map<string, string[]>(); // from -> [to] (dependents)

  for (const s of scenes) {
    if (!inDegree.has(s.id)) inDegree.set(s.id, 0);
    if (!adjList.has(s.id)) adjList.set(s.id, []);
    for (const dep of s.dependsOn) {
      inDegree.set(s.id, (inDegree.get(s.id) ?? 0) + 1);
      if (!adjList.has(dep)) adjList.set(dep, []);
      adjList.get(dep)!.push(s.id);
    }
  }

  const queue: string[] = [];
  for (const [id, deg] of inDegree.entries()) {
    if (deg === 0) queue.push(id);
  }

  // Sort by scene number for deterministic output
  queue.sort((a, b) => (idToScene.get(a)?.sceneNumber ?? 0) - (idToScene.get(b)?.sceneNumber ?? 0));

  const result: string[] = [];
  while (queue.length > 0) {
    const current = queue.shift()!;
    result.push(current);
    for (const neighbor of (adjList.get(current) ?? [])) {
      const newDeg = (inDegree.get(neighbor) ?? 1) - 1;
      inDegree.set(neighbor, newDeg);
      if (newDeg === 0) {
        queue.push(neighbor);
        queue.sort((a, b) => (idToScene.get(a)?.sceneNumber ?? 0) - (idToScene.get(b)?.sceneNumber ?? 0));
      }
    }
  }

  return result;
}

/** Groups scenes that share the same "dependency depth" and can run in parallel. */
export function buildConcurrentGroups(scenes: Scene[], executionOrder: string[]): string[][] {
  const idToScene = new Map(scenes.map((s) => [s.id, s]));
  const depth = new Map<string, number>();

  for (const id of executionOrder) {
    const scene = idToScene.get(id);
    if (!scene) continue;
    const maxDepDept = scene.dependsOn.reduce((max, dep) => Math.max(max, (depth.get(dep) ?? 0)), -1);
    depth.set(id, maxDepDept + 1);
  }

  const groups: Map<number, string[]> = new Map();
  for (const [id, d] of depth.entries()) {
    if (!groups.has(d)) groups.set(d, []);
    groups.get(d)!.push(id);
  }

  return Array.from(groups.entries())
    .sort(([a], [b]) => a - b)
    .map(([, ids]) => ids);
}

/** Returns true if all dependencies for a scene are in a completed/approved/skipped status. */
export function areDependenciesMet(scene: Scene, sceneMap: Map<string, Scene>): boolean {
  const doneStatuses: SceneStatus[] = ["completed", "approved", "skipped"];
  return scene.dependsOn.every((depId) => {
    const dep = sceneMap.get(depId);
    return dep && doneStatuses.includes(dep.status);
  });
}

/** Builds the full DependencyGraph structure for display. */
export function buildDependencyGraph(scenes: Scene[]): DependencyGraph {
  const executionOrder = buildExecutionOrder(scenes);
  const concurrentGroups = buildConcurrentGroups(scenes, executionOrder);

  return {
    nodes: scenes.map((s) => ({
      id: s.id,
      sceneNumber: s.sceneNumber,
      title: s.title,
      status: s.status
    })),
    edges: scenes.flatMap((s) => s.dependsOn.map((dep) => ({ from: dep, to: s.id }))),
    executionOrder,
    concurrentGroups
  };
}

/** Returns scenes ready to run (deps met, status is pending or waiting_deps). */
export function getReadyScenes(scenes: Scene[]): Scene[] {
  const sceneMap = new Map(scenes.map((s) => [s.id, s]));
  return scenes.filter(
    (s) =>
      (s.status === "pending" || s.status === "waiting_deps") &&
      areDependenciesMet(s, sceneMap)
  );
}
