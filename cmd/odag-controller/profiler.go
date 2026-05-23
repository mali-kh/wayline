package main

import (
	"database/sql"
	"fmt"
	"log"
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

// initProfilerDB opens (or creates) the profiler SQLite database and ensures
// all required tables exist. Returns the open *sql.DB handle.
func initProfilerDB(dbPath string) (*sql.DB, error) {
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, fmt.Errorf("open profiler db: %w", err)
	}

	// WAL mode allows concurrent readers while writing.
	if _, err := db.Exec("PRAGMA journal_mode=WAL"); err != nil {
		db.Close()
		return nil, fmt.Errorf("set WAL mode: %w", err)
	}
	// Set busy timeout so concurrent writes don't fail immediately.
	if _, err := db.Exec("PRAGMA busy_timeout=5000"); err != nil {
		db.Close()
		return nil, fmt.Errorf("set busy_timeout: %w", err)
	}

	// task_profiles: EMA-smoothed runtime and data size per (template, task, node).
	if _, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS task_profiles (
			template   TEXT    NOT NULL,
			task       TEXT    NOT NULL,
			node       TEXT    NOT NULL,
			runtime    REAL    NOT NULL,
			data_bytes REAL    NOT NULL DEFAULT 0,
			samples    INTEGER NOT NULL DEFAULT 1,
			updated_at TEXT    NOT NULL DEFAULT (datetime('now')),
			PRIMARY KEY (template, task, node)
		)
	`); err != nil {
		db.Close()
		return nil, fmt.Errorf("create task_profiles: %w", err)
	}

	// link_profiles: EMA-smoothed transfer metrics per (template, edge, node pair).
	if _, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS link_profiles (
			template     TEXT    NOT NULL,
			src_task     TEXT    NOT NULL,
			dst_task     TEXT    NOT NULL,
			src_node     TEXT    NOT NULL,
			dst_node     TEXT    NOT NULL,
			data_bytes   REAL    NOT NULL DEFAULT 0,
			transfer_sec REAL    NOT NULL DEFAULT 0,
			samples      INTEGER NOT NULL DEFAULT 1,
			updated_at   TEXT    NOT NULL DEFAULT (datetime('now')),
			PRIMARY KEY (template, src_task, dst_task, src_node, dst_node)
		)
	`); err != nil {
		db.Close()
		return nil, fmt.Errorf("create link_profiles: %w", err)
	}

	// image_profiles: EMA-smoothed runtime per (image, node) — shared across templates.
	if _, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS image_profiles (
			image      TEXT    NOT NULL,
			node       TEXT    NOT NULL,
			runtime    REAL    NOT NULL,
			data_bytes REAL    NOT NULL DEFAULT 0,
			samples    INTEGER NOT NULL DEFAULT 1,
			updated_at TEXT    NOT NULL DEFAULT (datetime('now')),
			PRIMARY KEY (image, node)
		)
	`); err != nil {
		db.Close()
		return nil, fmt.Errorf("create image_profiles: %w", err)
	}

	// run_counter: atomic auto-increment run number per template.
	if _, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS run_counter (
			template TEXT PRIMARY KEY,
			count    INTEGER NOT NULL DEFAULT 0
		)
	`); err != nil {
		db.Close()
		return nil, fmt.Errorf("create run_counter: %w", err)
	}

	log.Printf("[profiler] database ready at %s", dbPath)
	return db, nil
}

// --------------------------------------------------------------------------
// Run counter
// --------------------------------------------------------------------------

// nextRunID atomically increments and returns the next run number for a template.
// Retries on SQLITE_BUSY: the busy_timeout pragma is per-connection and Go's
// pool may hand out a connection that doesn't see another connection's lock,
// so back off and retry a few times to cover bursts of concurrent run creations.
func nextRunID(db *sql.DB, template string) (int, error) {
	var lastErr error
	for attempt := 0; attempt < 8; attempt++ {
		if attempt > 0 {
			time.Sleep(time.Duration(50*(1<<attempt)) * time.Millisecond)
		}
		var count int
		err := db.QueryRow(`
			INSERT INTO run_counter (template, count) VALUES (?, 1)
			ON CONFLICT(template) DO UPDATE SET count = count + 1
			RETURNING count
		`, template).Scan(&count)
		if err == nil {
			return count, nil
		}
		lastErr = err
		if !strings.Contains(err.Error(), "database is locked") &&
			!strings.Contains(err.Error(), "SQLITE_BUSY") {
			break
		}
	}
	return 0, fmt.Errorf("nextRunID: %w", lastErr)
}

// --------------------------------------------------------------------------
// Task profile recording (EMA)
// --------------------------------------------------------------------------

// recordTaskProfile upserts a task runtime observation using exponential moving average.
//
//	new_ema = alpha * observed + (1 - alpha) * old_ema
//
// If no row exists yet, the first observation is used directly.
// The samples counter is capped at maxSamples.
func recordTaskProfile(db *sql.DB, template, task, node string,
	observedRuntime float64, observedDataBytes float64,
	alpha float64, maxSamples int) error {

	_, err := db.Exec(`
		INSERT INTO task_profiles (template, task, node, runtime, data_bytes, samples, updated_at)
		VALUES (?, ?, ?, ?, ?, 1, datetime('now'))
		ON CONFLICT(template, task, node) DO UPDATE SET
			runtime    = ? * ? + (1.0 - ?) * runtime,
			data_bytes = CASE WHEN ? > 0 THEN ? * ? + (1.0 - ?) * data_bytes ELSE data_bytes END,
			samples    = MIN(samples + 1, ?),
			updated_at = datetime('now')
	`, template, task, node, observedRuntime, observedDataBytes,
		alpha, observedRuntime, alpha,
		observedDataBytes, alpha, observedDataBytes, alpha,
		maxSamples)
	if err != nil {
		return fmt.Errorf("recordTaskProfile: %w", err)
	}
	return nil
}

// --------------------------------------------------------------------------
// Image profile recording (EMA) — shared across templates
// --------------------------------------------------------------------------

// recordImageProfile upserts a runtime observation keyed by (image, node).
// This allows templates sharing the same task image to benefit from each other's data.
func recordImageProfile(db *sql.DB, image, node string,
	observedRuntime float64, observedDataBytes float64,
	alpha float64, maxSamples int) error {

	_, err := db.Exec(`
		INSERT INTO image_profiles (image, node, runtime, data_bytes, samples, updated_at)
		VALUES (?, ?, ?, ?, 1, datetime('now'))
		ON CONFLICT(image, node) DO UPDATE SET
			runtime    = ? * ? + (1.0 - ?) * runtime,
			data_bytes = CASE WHEN ? > 0 THEN ? * ? + (1.0 - ?) * data_bytes ELSE data_bytes END,
			samples    = MIN(samples + 1, ?),
			updated_at = datetime('now')
	`, image, node, observedRuntime, observedDataBytes,
		alpha, observedRuntime, alpha,
		observedDataBytes, alpha, observedDataBytes, alpha,
		maxSamples)
	if err != nil {
		return fmt.Errorf("recordImageProfile: %w", err)
	}
	return nil
}

// --------------------------------------------------------------------------
// Link profile recording (EMA)
// --------------------------------------------------------------------------

// recordLinkProfile upserts a data transfer observation between two nodes.
func recordLinkProfile(db *sql.DB, template, srcTask, dstTask, srcNode, dstNode string,
	observedBytes float64, observedTransferSec float64,
	alpha float64, maxSamples int) error {

	if srcNode == dstNode {
		return nil // same-node transfer: nothing to profile
	}

	_, err := db.Exec(`
		INSERT INTO link_profiles (template, src_task, dst_task, src_node, dst_node,
			data_bytes, transfer_sec, samples, updated_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
		ON CONFLICT(template, src_task, dst_task, src_node, dst_node) DO UPDATE SET
			data_bytes   = ? * ? + (1.0 - ?) * data_bytes,
			transfer_sec = ? * ? + (1.0 - ?) * transfer_sec,
			samples      = MIN(samples + 1, ?),
			updated_at   = datetime('now')
	`, template, srcTask, dstTask, srcNode, dstNode,
		observedBytes, observedTransferSec,
		alpha, observedBytes, alpha,
		alpha, observedTransferSec, alpha,
		maxSamples)
	if err != nil {
		return fmt.Errorf("recordLinkProfile: %w", err)
	}
	return nil
}

// --------------------------------------------------------------------------
// Task profile queries
// --------------------------------------------------------------------------

// TaskProfile holds a single profiled runtime entry.
type TaskProfile struct {
	Runtime   float64
	DataBytes float64
	Samples   int
}

// getTaskProfile returns the profiled runtime for a (template, task, node) tuple.
// Returns the profile and true if found, or zero-value and false if not.
func getTaskProfile(db *sql.DB, template, task, node string) (TaskProfile, bool) {
	var p TaskProfile
	err := db.QueryRow(`
		SELECT runtime, data_bytes, samples FROM task_profiles
		WHERE template = ? AND task = ? AND node = ?
	`, template, task, node).Scan(&p.Runtime, &p.DataBytes, &p.Samples)
	if err != nil {
		return TaskProfile{}, false
	}
	return p, true
}

// getTaskProfiles returns all profiled entries for a template.
// Result: map[taskName]map[nodeName]TaskProfile
func getTaskProfiles(db *sql.DB, template string) map[string]map[string]TaskProfile {
	rows, err := db.Query(`
		SELECT task, node, runtime, data_bytes, samples FROM task_profiles
		WHERE template = ?
	`, template)
	if err != nil {
		return nil
	}
	defer rows.Close()

	result := make(map[string]map[string]TaskProfile)
	for rows.Next() {
		var task, node string
		var p TaskProfile
		if err := rows.Scan(&task, &node, &p.Runtime, &p.DataBytes, &p.Samples); err != nil {
			continue
		}
		if result[task] == nil {
			result[task] = make(map[string]TaskProfile)
		}
		result[task][node] = p
	}
	return result
}

// --------------------------------------------------------------------------
// Link profile queries
// --------------------------------------------------------------------------

// LinkProfile holds a single profiled link transfer entry.
type LinkProfile struct {
	DataBytes   float64
	TransferSec float64
	Samples     int
}

// getLinkProfiles returns all profiled link entries for a template.
func getLinkProfiles(db *sql.DB, template string) []LinkProfile {
	rows, err := db.Query(`
		SELECT data_bytes, transfer_sec, samples FROM link_profiles
		WHERE template = ?
	`, template)
	if err != nil {
		return nil
	}
	defer rows.Close()

	var result []LinkProfile
	for rows.Next() {
		var p LinkProfile
		if err := rows.Scan(&p.DataBytes, &p.TransferSec, &p.Samples); err != nil {
			continue
		}
		result = append(result, p)
	}
	return result
}

// --------------------------------------------------------------------------
// Image profile queries
// --------------------------------------------------------------------------

// ImageProfile holds a single profiled runtime entry keyed by image.
type ImageProfile struct {
	Runtime   float64
	DataBytes float64
	Samples   int
}

// getImageProfile returns the profiled runtime for an (image, node) pair.
func getImageProfile(db *sql.DB, image, node string) (ImageProfile, bool) {
	var p ImageProfile
	err := db.QueryRow(`
		SELECT runtime, data_bytes, samples FROM image_profiles
		WHERE image = ? AND node = ?
	`, image, node).Scan(&p.Runtime, &p.DataBytes, &p.Samples)
	if err != nil {
		return ImageProfile{}, false
	}
	return p, true
}

// --------------------------------------------------------------------------
// Link bandwidth query — cross-template aggregation
// --------------------------------------------------------------------------

// getLinkBandwidthBetween computes the profiler-observed bandwidth (bytes/sec)
// between two nodes by aggregating link_profiles across all templates.
// Returns (bandwidth, true) if sufficient data exists, (0, false) otherwise.
func getLinkBandwidthBetween(db *sql.DB, srcNode, dstNode string, minSamples int) (float64, bool) {
	if db == nil || srcNode == dstNode {
		return 0, false
	}
	var totalBytes, totalSec float64
	var count int
	rows, err := db.Query(`
		SELECT data_bytes, transfer_sec, samples FROM link_profiles
		WHERE src_node = ? AND dst_node = ? AND samples >= ? AND transfer_sec > 0
	`, srcNode, dstNode, minSamples)
	if err != nil {
		return 0, false
	}
	defer rows.Close()
	for rows.Next() {
		var bytes, sec float64
		var s int
		if err := rows.Scan(&bytes, &sec, &s); err != nil {
			continue
		}
		totalBytes += bytes
		totalSec += sec
		count++
	}
	if count == 0 || totalSec <= 0 {
		return 0, false
	}
	return totalBytes / totalSec, true
}

// --------------------------------------------------------------------------
// Runtime resolver — used by HEFT scheduler
// --------------------------------------------------------------------------

// buildRuntimeResolver creates a function that resolves the expected runtime
// for a (task, node) pair using this priority chain:
//  1. Template-specific profile (template, task, node) — if samples >= minSamples
//  2. Image-based profile (image, node) — shared across templates
//  3. Task spec hint (runtime field from the ODAG/template)
//  4. Template default runtime
//  5. Hardcoded fallback (10s)
//
// If runtimeSource is "manual", profiler steps (1,2) are skipped.
func buildRuntimeResolver(db *sql.DB, template string, tasks []taskSpec,
	minSamples int, defaultRuntime float64, runtimeSource string) func(taskName, nodeName string) float64 {

	specHints := make(map[string]float64, len(tasks))
	specProfiles := make(map[string]map[string]float64, len(tasks))
	imageByTask := make(map[string]string, len(tasks))
	for _, t := range tasks {
		if t.Runtime > 0 {
			specHints[t.Name] = t.Runtime
		}
		if len(t.RuntimeProfile) > 0 {
			specProfiles[t.Name] = t.RuntimeProfile
		}
		imageByTask[t.Name] = t.Image
	}

	if defaultRuntime <= 0 {
		defaultRuntime = 10.0
	}

	useProfiler := runtimeSource != "manual"

	return func(taskName, nodeName string) float64 {
		if useProfiler && db != nil {
			// 1. Template-specific profile (from profiler DB)
			if template != "" {
				if p, ok := getTaskProfile(db, template, taskName, nodeName); ok && p.Samples >= minSamples {
					return p.Runtime
				}
			}
			// 2. Image-based profile (from profiler DB)
			if img := imageByTask[taskName]; img != "" {
				if p, ok := getImageProfile(db, img, nodeName); ok && p.Samples >= minSamples {
					return p.Runtime
				}
			}
		}
		// 3. Per-node runtime hint from spec (runtimeProfile field)
		if prof, ok := specProfiles[taskName]; ok {
			if rt, ok := prof[nodeName]; ok {
				return rt
			}
		}
		// 4. Scalar runtime hint from spec
		if hint, ok := specHints[taskName]; ok {
			return hint
		}
		// 5. Template default
		return defaultRuntime
	}
}

// buildDataSizeResolver creates a function that resolves the expected output
// data size in bytes for a task, using profiler data or spec hints.
func buildDataSizeResolver(db *sql.DB, template string, tasks []taskSpec,
	minSamples int, defaultDataSize string, runtimeSource string) func(taskName, nodeName string) int64 {

	specHints := make(map[string]int64, len(tasks))
	imageByTask := make(map[string]string, len(tasks))
	for _, t := range tasks {
		if b := parseDataSizeBytes(t.DataSize); b > 0 {
			specHints[t.Name] = b
		}
		imageByTask[t.Name] = t.Image
	}

	defaultBytes := parseDataSizeBytes(defaultDataSize)
	useProfiler := runtimeSource != "manual"

	return func(taskName, nodeName string) int64 {
		if useProfiler && db != nil {
			// 1. Template-specific profile
			if template != "" {
				if p, ok := getTaskProfile(db, template, taskName, nodeName); ok && p.Samples >= minSamples && p.DataBytes > 0 {
					return int64(p.DataBytes)
				}
			}
			// 2. Image-based profile
			if img := imageByTask[taskName]; img != "" {
				if p, ok := getImageProfile(db, img, nodeName); ok && p.Samples >= minSamples && p.DataBytes > 0 {
					return int64(p.DataBytes)
				}
			}
		}
		// 3. Spec hint
		if hint, ok := specHints[taskName]; ok {
			return hint
		}
		// 4. Default
		return defaultBytes
	}
}
