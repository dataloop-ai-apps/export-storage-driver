import os
import logging
import json
from io import BytesIO
import multiprocessing
import threading
import dtlpy as dl

logger = logging.getLogger(__name__)


class ExportStorageDriver(dl.BaseServiceRunner):
    def __init__(self):
        """
        Initialize the ExportStorageDriver.
        """
        self.datasets_dict = self._get_system_datasets()
        self.dataset_locks = {}  # Dictionary to store locks for each dataset
        self._initialize_dataset_locks()

        # Start the cleaning process from init
        print("Starting dataset cleaning in separate process from init...")
        cleaning_process = multiprocessing.Process(target=self.clean_datasets_process)
        cleaning_process.start()

        # Wait for the process to complete
        cleaning_process.join()

        if cleaning_process.exitcode == 0:
            print("Dataset cleaning process completed successfully")
        else:
            print(f"Dataset cleaning process failed with exit code: {cleaning_process.exitcode}")

    def _initialize_dataset_locks(self):
        """
        Initialize mutex locks for each dataset in datasets_dict.
        """
        for dataset_name in self.datasets_dict.keys():
            self.dataset_locks[dataset_name] = threading.Lock()

    def _get_system_datasets(self):
        project = self.service_entity.project
        filters = dl.Filters(resource=dl.FiltersResource.DATASET)
        filters.system_space = True
        filters.add(field="metadata.system.exportSolution", values=True)
        datasets = project.datasets.list(filters=filters)
        datasets_dict = {dataset.name: dataset for dataset in datasets}
        return datasets_dict

    def clean_system_datasets(self):
        for dataset_name, dataset in self.datasets_dict.items():
            # Use mutex lock for each dataset
            with self.dataset_locks.get(dataset_name, threading.Lock()):
                logger.info(f"Cleaning items from dataset {dataset_name}")
                dataset.items.delete(filters=dl.Filters())

    def _create_system_dataset(self, item: dl.Item, driver_id: str) -> dl.Dataset:
        """
        Create a system dataset linked to the storage driver.
        """
        try:
            dataset_name = f"Export Storage Driver - {driver_id}"
            # Use mutex lock for dataset creation/access
            if dataset_name not in self.dataset_locks:
                self.dataset_locks[dataset_name] = threading.Lock()

            with self.dataset_locks[dataset_name]:
                dataset = self.datasets_dict[dataset_name]
        except KeyError:
            with self.dataset_locks.get(dataset_name, threading.Lock()):
                driver = dl.drivers.get(driver_id=driver_id)
                dataset = item.project.datasets.create(dataset_name=dataset_name, driver=driver)
                dataset.metadata["system"]["scope"] = "system"
                dataset.metadata["system"]["exportSolution"] = True
                dataset.update(True)
                self.datasets_dict[dataset_name] = dataset
                # Ensure lock exists for the new dataset
                if dataset_name not in self.dataset_locks:
                    self.dataset_locks[dataset_name] = threading.Lock()
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

        upload_result = system_dataset.items.upload(local_path=json_buffer, remote_name=filename, remote_path=item.dir, raise_on_error=True)
        print(f"Data uploaded as '{item.name}' successfully using BytesIO")

        if upload_result is not None:
            upload_result.delete()
        return upload_result

    def clean_datasets_process(self):
        """
        Class method to run clean_system_datasets in a separate process.
        """
        try:
            # Initialize the datasets and locks for this process
            datasets_dict = self._get_system_datasets()
            dataset_locks = {}

            # Initialize locks for each dataset
            for dataset_name in datasets_dict.keys():
                dataset_locks[dataset_name] = threading.Lock()

            # Clean the datasets with proper locking
            for dataset_name, dataset in datasets_dict.items():
                with dataset_locks.get(dataset_name, threading.Lock()):
                    logger.info(f"Cleaning items from dataset {dataset_name}")
                    dataset.items.delete(filters=dl.Filters())

            print("Dataset cleaning completed in separate process")
        except Exception as e:
            logger.error(f"Error in clean_datasets_process: {e}")
            print(f"Error cleaning datasets: {e}")


def main():
    """
    Main function for testing purposes.
    """
    # Create an instance of ExportStorageDriver
    # The cleaning process will be started automatically from __init__
    driver = ExportStorageDriver()
    print("ExportStorageDriver initialized and dataset cleaning completed")


if __name__ == "__main__":
    main()
