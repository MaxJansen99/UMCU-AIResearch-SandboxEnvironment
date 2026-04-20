from idc_index import IDCClient

client = IDCClient()

# get identifiers of all collections available in IDC
all_collection_ids = client.get_collections()

# download files for the specific collection, patient, study or series
                               
client.download_from_selection(
     studyInstanceUID="1.3.6.1.4.1.14519.5.2.1.207544490797667703011829289839681390478",
     downloadDir="/Users/pierre/school/HU/AI/inno/tool/idc-data/")
                               
