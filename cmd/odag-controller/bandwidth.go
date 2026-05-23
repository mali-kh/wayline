package main

import (
	"context"
	"database/sql"
	"log"
	"strconv"
	"strings"
	"sync"
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
)

// Default bandwidth for node pairs not in any source.
const heftDefaultBandwidth = 125_000_000.0 // 125 MB/s (1 Gbps)

const (
	networkConfigMapName = "wl-network-profile"
	networkConfigMapNS   = "wl-system"
)

// --------------------------------------------------------------------------
// ConfigMap-backed bandwidth cache
// --------------------------------------------------------------------------

var (
	bandwidthMu      sync.RWMutex
	bandwidthCache   = make(map[string]float64) // "srcNode->dstNode" -> bytes/sec
	bandwidthDefault = heftDefaultBandwidth
)

// watchBandwidthConfigMap watches the wl-network-profile ConfigMap and
// updates the in-memory bandwidth cache on every change.
func watchBandwidthConfigMap(client *kubernetes.Clientset) {
	// Initial load.
	loadBandwidthConfigMap(client)

	for {
		watcher, err := client.CoreV1().ConfigMaps(networkConfigMapNS).Watch(
			context.Background(), metav1.ListOptions{
				FieldSelector: "metadata.name=" + networkConfigMapName,
			},
		)
		if err != nil {
			log.Printf("[bandwidth] error watching ConfigMap: %v; retrying in 5s", err)
			time.Sleep(5 * time.Second)
			continue
		}
		log.Println("[bandwidth] watching wl-network-profile ConfigMap")
		for event := range watcher.ResultChan() {
			if string(event.Type) == "DELETED" {
				bandwidthMu.Lock()
				bandwidthCache = make(map[string]float64)
				bandwidthDefault = heftDefaultBandwidth
				bandwidthMu.Unlock()
				log.Println("[bandwidth] ConfigMap deleted; using defaults")
				continue
			}
			loadBandwidthConfigMap(client)
		}
		log.Println("[bandwidth] ConfigMap watcher closed; reconnecting in 2s")
		time.Sleep(2 * time.Second)
	}
}

// loadBandwidthConfigMap reads the ConfigMap and populates the cache.
func loadBandwidthConfigMap(client *kubernetes.Clientset) {
	cm, err := client.CoreV1().ConfigMaps(networkConfigMapNS).Get(
		context.Background(), networkConfigMapName, metav1.GetOptions{},
	)
	if err != nil {
		log.Printf("[bandwidth] ConfigMap %s/%s not found; using defaults", networkConfigMapNS, networkConfigMapName)
		return
	}

	newCache := make(map[string]float64)
	newDefault := heftDefaultBandwidth

	for key, val := range cm.Data {
		if key == "defaultBandwidth" {
			if f, err := strconv.ParseFloat(val, 64); err == nil && f > 0 {
				newDefault = f
			}
			continue
		}
		// Expect keys like "anrg-3_to_anrg-5"; store internally as "anrg-3->anrg-5".
		if !strings.Contains(key, "_to_") {
			continue
		}
		internalKey := strings.Replace(key, "_to_", "->", 1)
		if f, err := strconv.ParseFloat(val, 64); err == nil && f > 0 {
			newCache[internalKey] = f
		}
	}

	bandwidthMu.Lock()
	bandwidthCache = newCache
	bandwidthDefault = newDefault
	bandwidthMu.Unlock()

	log.Printf("[bandwidth] loaded %d link entries from ConfigMap (default: %.0f B/s)", len(newCache), newDefault)
}

// getConfigMapBandwidth returns the bandwidth for a node pair from the ConfigMap cache.
func getConfigMapBandwidth(src, dst string) (float64, bool) {
	bandwidthMu.RLock()
	defer bandwidthMu.RUnlock()
	bw, ok := bandwidthCache[src+"->"+dst]
	return bw, ok
}

// getConfigMapDefault returns the default bandwidth from the ConfigMap.
func getConfigMapDefault() float64 {
	bandwidthMu.RLock()
	defer bandwidthMu.RUnlock()
	return bandwidthDefault
}

// --------------------------------------------------------------------------
// Bandwidth resolver — used by HEFT scheduler
// --------------------------------------------------------------------------

// bandwidthResolver returns the bandwidth in bytes/sec between two nodes.
type bandwidthResolver func(srcNode, dstNode string) float64

// buildBandwidthResolver creates a bandwidth resolver function based on the
// configured source:
//
//   - "external": ConfigMap only → default
//   - "profiler": profiler link_profiles only → default
//   - "hybrid":   profiler → ConfigMap → default
func buildBandwidthResolver(db *sql.DB, minSamples int, source string) bandwidthResolver {
	return func(src, dst string) float64 {
		if src == dst {
			return 0 // same node: no network transfer
		}

		switch source {
		case "profiler":
			if bw, ok := getLinkBandwidthBetween(db, src, dst, minSamples); ok {
				return bw
			}
		case "hybrid":
			if bw, ok := getLinkBandwidthBetween(db, src, dst, minSamples); ok {
				return bw
			}
			if bw, ok := getConfigMapBandwidth(src, dst); ok {
				return bw
			}
		default: // "external"
			if bw, ok := getConfigMapBandwidth(src, dst); ok {
				return bw
			}
		}

		return getConfigMapDefault()
	}
}
