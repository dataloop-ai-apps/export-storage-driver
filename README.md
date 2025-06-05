# Export Using Dataloop Storage Driver

This application is designed to create a generic export node to the Dataloop pipelines.
The generic solution will be based on the Dataloop's Storage Drivers by creating a dedicated hidden dataset to export items (metadata) and annotations from Dataloop to any external storage

---

## Architecture Overview

This project uses a **modular service with worker pattern** for scalability, reliability, and extensibility.

### Main Components
- **Core Controller:** Manages configuration, dataset lifecycle, and orchestration. Cleans up orphaned hidden datasets on startup.
- **Export Worker(s):** Poll for new items to export. Export item metadata and annotations as a single JSON to the correct path. Handle export failures with retries and logging.
- **Cleanup Handler:** Supports multiple cleanup strategies (configurable). Can be triggered by schedule, signal, or post-upload logic.

### Data Flow
1. Items are triggered for export manually of from a Pipeline node.
2. Export workers process items, exporting metadata and annotations as a single JSON file.
3. Cleanup handler removes items or datasets based on configured strategy.

---

## Creating a Driver

### Dataloop Storage Driver

1. must be with allow delete - False

### Hidden dataset creation

1. name convention - maybe driver id
2. check if exists before creating

### Export Content

We will export the item metadata and annotations in a single json, to the same original path from dataloop:
```python
export_json = item.to_json()
export_json['annotations'] = item.annotations.list().to_json()['annotations']
```

## Cleanup

### Items Cleanup

Options:

1. scheduled weekly - delete all the items
2. SIGTEM - delete all the items
3. delete directly after upload
4. after upload - check dataset count and if above a threshold - delete all the items

### Dataset Cleanup

On each `init` - list all the hidden datasets and check if the storage driver still exists. if not - delete the dataset

## Implementation Guidelines

- Use the modular service pattern for scalability and reliability.
- Define clear interfaces for storage drivers and export formats.
- Ensure robust error handling and logging throughout the export and cleanup processes.
- Make all operational parameters configurable.
- Prioritize security and observability in all components.
