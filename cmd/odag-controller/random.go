package main

import (
	"log"
	"math/rand"
)

// assignTasks picks a random node from the allowed set for each task.
func assignTasks(tasks []taskSpec, nodeMap map[string]nodeInfo) map[string]nodeInfo {
	allNames := make([]string, 0, len(nodeMap))
	for name := range nodeMap {
		allNames = append(allNames, name)
	}

	result := make(map[string]nodeInfo, len(tasks))
	for _, t := range tasks {
		candidates := allNames
		if len(t.Constraints) > 0 {
			var allowed []string
			for _, c := range t.Constraints {
				if _, ok := nodeMap[c]; ok {
					allowed = append(allowed, c)
				}
			}
			if len(allowed) > 0 {
				candidates = allowed
			} else {
				log.Printf("[random] task %s: no constraint nodes in cluster; using any node", t.Name)
			}
		}
		chosen := candidates[rand.Intn(len(candidates))]
		result[t.Name] = nodeMap[chosen]
	}
	return result
}
