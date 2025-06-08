import os
import json
from io import BytesIO
import dtlpy as dl


class ExportStorageDriver(dl.BaseServiceRunner):
    def __init__(self):
        """
        Initialize the ExportStorageDriver.
        """
        self.clean_system_datasets()

    def clean_system_datasets(self):
        project = self.service_entity.project
        filters = dl.Filters(resource=dl.FiltersResource.DATASET)
        filters.system_space = True
        filters.add(field="metadata.system.exportSolution", values=True)
        datasets = project.datasets.list(filters=filters)
        for dataset in datasets:
            self._delete_dataset_items(dataset)

    def _create_system_dataset(self, item: dl.Item, driver_id: str) -> None:
        """
        Create a system dataset linked to the storage driver.
        """
        try:
            filters = dl.Filters(resource=dl.FiltersResource.DATASET)
            filters.add(field="name", values=driver_id)
            filters.system_space = True
            dataset = item.project.datasets.list(filters=filters)[0]
            print("System dataset already exists")
        except IndexError:
            driver = dl.drivers.get(driver_id=driver_id)
            dataset = item.project.datasets.create(dataset_name=driver.id, driver=driver)
            dataset.metadata["system"]["scope"] = "system"
            dataset.metadata["system"]["exportSolution"] = True
            dataset.update(True)
            print("System dataset created successfully")
        return dataset

    def export_data(self, item: dl.Item, context: dl.Context) -> None:
        """
        Upload data from local path to the dataset.

        Args:
            item: The item to export
            context: The context of the item
        """

        node_context = context.node
        driver_id = node_context.metadata.get("customNodeConfig", dict()).get("storageDriverId", None)
        if driver_id is None:
            raise ValueError("Driver ID is not set")

        system_dataset = self._create_system_dataset(item=item, driver_id=driver_id)

        item_json = item.to_json()
        item_json["annotations"] = item.annotations.list().to_json()["annotations"]
        filename, _ = os.path.splitext(item.name)
        filename = f"{filename}.json"

        json_bytes = json.dumps(item_json, indent=2).encode("utf-8")
        json_buffer = BytesIO(json_bytes)

        upload_result = system_dataset.items.upload(local_path=json_buffer, remote_name=item.name, remote_path=item.dir)
        print(f"Data uploaded as '{item.name}' successfully using BytesIO")

        if upload_result is not None:
            upload_result.delete()
        return upload_result

    def _delete_dataset_items(self, dataset: dl.Dataset) -> bool:
        """
        Delete all items from the dataset.
        Note: Files will remain in S3 bucket due to allow_external_delete=False.

        Returns:
            bool: True if deletion successful
        """
        result = dataset.items.delete(filters=dl.Filters())
        print("Items deleted from Dataloop (files remain in S3 bucket)")
        return result
