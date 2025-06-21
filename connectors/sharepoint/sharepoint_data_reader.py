"""
Copyright (c) 2023 Liam Cavanagh

This code is an adaptation of the original code available at https://github.com/liamca/sharepoint-indexing-azure-cognitive-search, licensed under the MIT License.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union, Tuple
import os

import msal
import requests
from dotenv import load_dotenv
import logging


class SharePointDataReader:
    """This class facilitates the extraction of data from SharePoint using Microsoft Graph API.
    It supports authentication and data retrieval from SharePoint sites, lists, and libraries.
    """

    def __init__(
        self,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        graph_uri: str = "https://graph.microsoft.com",
        authority_template: str = "https://login.microsoftonline.com/{tenant_id}",
    ):
        """
        Initialize the SharePointDataExtractor class with optional environment variables.

        :param tenant_id: Tenant ID for Microsoft 365.
        :param client_id: Client ID for the application registered in Azure AD.
        :param client_secret: Client secret for the application registered in Azure AD.
        :param graph_uri: URI for Microsoft Graph API.
        :param authority_template: Template for authority URL used in authentication.
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.graph_uri = graph_uri
        self.authority = (
            authority_template.format(tenant_id=tenant_id) if tenant_id else None
        )
        self.scope = ["https://graph.microsoft.com/.default"]
        self.access_token = None

        # Add diagnostic logging for authentication variables
        self._log_auth_diagnostic()

    def load_environment_variables_from_env_file(self):
        """
        Loads required SharePoint credentials from environment variables if not already set.
        Supports both AZURE_* and SHAREPOINT_* prefixed variable naming.
        """
        if not self.tenant_id:
            # Try both possible env var names for tenant_id
            self.tenant_id = os.getenv("AZURE_TENANT_ID") or os.getenv("SHAREPOINT_TENANT_ID")
            
        if not self.client_id:
            # Try both possible env var names for client_id
            self.client_id = os.getenv("SHAREPOINT_CLIENT_ID") or os.getenv("AZURE_CLIENT_ID")
            
        # Load certificate-based authentication details
        cert_path = os.getenv("AGENTIC_APP_SPN_CERT_PATH")
        cert_password = os.getenv("AGENTIC_APP_SPN_CERT_PASSWORD")
        
        # Check if certificate exists
        cert_exists = cert_path and os.path.exists(cert_path)
        
        # Set client_secret for certificate-based auth if available
        if cert_exists and cert_password and not self.client_secret:
            logging.info("[sharepoint_files_reader] Certificate path exists, using certificate-based authentication")
            self.client_secret = {"thumbprint": "", "private_key": cert_path, "password": cert_password}
            
        # Look for regular client secret if certificate not available
        if not self.client_secret:
            self.client_secret = os.getenv("SHAREPOINT_CLIENT_SECRET") or os.getenv("SHAREPOINT_CLIENT_SECRET_VALUE") or os.getenv("SHAREPOINT_CLIENT_SECRET_NAME")
            
        if not self.authority:
            tenant_id = self.tenant_id
            self.authority = f"https://login.microsoftonline.com/{tenant_id}" if tenant_id else None
            
        # Try authentication with available credentials
        if not self.access_token:
            if self.tenant_id and self.client_id:
                logging.info("[sharepoint_files_reader] Attempting authentication with available credentials")
                
                # Try certificate-based auth if configured
                if isinstance(self.client_secret, dict) and cert_exists:
                    try:
                        token = self._msgraph_auth()
                        if token:
                            logging.info("[sharepoint_files_reader] Successfully authenticated with certificate")
                            return
                        else:
                            logging.warning("[sharepoint_files_reader] Certificate authentication failed")
                    except Exception as e:
                        logging.error(f"[sharepoint_files_reader] Certificate authentication error: {e}")
                
                # Try regular client secret if available
                elif isinstance(self.client_secret, str) and self.client_secret:
                    try:
                        token = self._msgraph_auth()
                        if token:
                            logging.info("[sharepoint_files_reader] Successfully authenticated with client secret")
                            return
                        else:
                            logging.warning("[sharepoint_files_reader] Client secret authentication failed")
                    except Exception as e:
                        logging.error(f"[sharepoint_files_reader] Client secret authentication error: {e}")
                
                # Fall back to interactive login
                logging.info("[sharepoint_files_reader] Attempting interactive login as fallback")
                token = self.interactive_login()
                if token:
                    logging.info("[sharepoint_files_reader] Interactive login successful")
                else:
                    logging.error("[sharepoint_files_reader] Interactive login failed. Check credentials or network connection.")
            else:
                logging.error("[sharepoint_files_reader] Missing tenant_id or client_id for authentication")

    def retrieve_sharepoint_files_content(
        self,
        site_domain: str,
        site_name: str,
        folder_path: Optional[str] = None,
        file_names: Optional[Union[str, List[str]]] = None,
        minutes_ago: Optional[int] = None,
        file_formats: Optional[List[str]] = None,
        drive_name: Optional[str] = None,  # NEW
    ) -> List[Dict[str, Any]]:
        """
        Retrieve contents of files from a specified SharePoint location, optionally filtering by last modification time and file formats.

        :param site_domain: The domain of the site in Microsoft Graph.
        :param site_name: The name of the site in Microsoft Graph.
        :param folder_path: Path to the folder within the drive, can include subfolders like 'test1/test2'.
        :param file_names: Optional; the name or names of specific files to retrieve. If provided, only these files' content will be fetched.
        :param minutes_ago: Optional; filter for files modified within the specified number of minutes.
        :param file_formats: Optional; list of desired file formats to include.
        :param drive_name: Optional; the name of the drive to retrieve files from. If not provided, the default drive will be used.
        :return: List of dictionaries with file metadata and content in bytes.
        """
        self.load_environment_variables_from_env_file()
        if self._are_required_variables_missing():
            return None

        site_id, drive_id = self._get_site_and_drive_ids(site_domain, site_name, drive_name)
        if not site_id or not drive_id:
            return None

        files = self._get_files(
            site_id, drive_id, folder_path, minutes_ago, file_formats
        )
        if not files:
            logging.info("[sharepoint_files_reader] No files found in the site's drive")
            return None

        return self._process_files(
            site_id, drive_id, folder_path, file_names, files, file_formats
        )

    def _msgraph_auth(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        authority: Optional[str] = None,
    ):
        """
        Authenticate with Microsoft Graph using MSAL for Python.
        Supports both regular client_secret and certificate-based authentication.
        """
        # Use provided parameters or fall back to instance attributes
        client_id = client_id or self.client_id
        client_secret = client_secret or self.client_secret
        authority = authority or self.authority
        
        # Check if all necessary credentials are provided
        if not all([client_id, client_secret, authority]):
            raise ValueError("Missing required authentication credentials.")
            
        # Handle different types of client_secret for certificate-based auth
        if isinstance(client_secret, dict):
            # Certificate-based authentication
            cert_path = client_secret.get("private_key")
            password = client_secret.get("password")
            
            if not cert_path or not os.path.exists(cert_path):
                logging.error(f"[sharepoint_files_reader] Certificate file not found: {cert_path}")
                return None
                
            try:
                with open(cert_path, "rb") as cert_file:
                    cert_bytes = cert_file.read()
                    
                app = msal.ConfidentialClientApplication(
                    client_id=client_id, 
                    authority=authority,
                    client_credential={"certificate": cert_bytes, "password": password}
                )
            except Exception as e:
                logging.error(f"[sharepoint_files_reader] Error loading certificate: {e}")
                return None
        else:
            # Regular client secret authentication
            app = msal.ConfidentialClientApplication(
                client_id=client_id, 
                authority=authority, 
                client_credential=client_secret
            )

        try:
            # Attempt to acquire token
            access_token = app.acquire_token_silent(self.scope, account=None)
            if not access_token:
                access_token = app.acquire_token_for_client(scopes=self.scope)
                if "access_token" in access_token:
                    logging.debug("[sharepoint_files_reader] New access token retrieved.")
                else:
                    error_msg = access_token.get("error_description", "Unknown error")
                    logging.error(f"[sharepoint_files_reader] Error acquiring authorization token: {error_msg}")
                    return None
            else:
                logging.debug("[sharepoint_files_reader] Token retrieved from MSAL Cache.")

            # Store the access token in the instance
            self.access_token = access_token["access_token"]
            return self.access_token

        except Exception as err:
            logging.error(f"[sharepoint_files_reader] Error in msgraph_auth: {err}")
            return None

    @staticmethod
    def _format_url(site_id: str, drive_id: str, folder_path: str = None) -> str:
        """
        Formats the URL for accessing a nested site drive in Microsoft Graph.

        :param site_id: The site ID in Microsoft Graph.
        :param drive_id: The drive ID in Microsoft Graph.
        :param folder_path: path to the folder within the drive, can include subfolders.
            The format should follow '/folder/subfolder1/subfolder2/'. For example,
            '/test/test1/test2/' to access nested folders.
        :return: The formatted URL.
        """
        # If folder_path is None, empty, or just "/" then return the root folder URL.
        if not folder_path or folder_path.strip() == "/":
            return f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/"
        
        # Otherwise, remove any trailing slashes and format the URL for a subfolder.
        folder_path_formatted = folder_path.rstrip("/")
        return f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:{folder_path_formatted}:/"

    def _make_ms_graph_request(
        self, url: str, access_token: Optional[str] = None
    ) -> Dict:
        """
        Make a request to the Microsoft Graph API.

        :param url: The URL for the Microsoft Graph API endpoint.
        :param access_token: Optional; The access token for Microsoft Graph API authentication. If not provided, uses the instance's stored token.
        :return: The JSON response from the Microsoft Graph API.
        :raises Exception: If there's an HTTP error or other issues in making the request.
        """
        access_token = access_token or self.access_token
        if not access_token:
            raise ValueError("Access token is required for making API requests.")

        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            logging.error(f"[sharepoint_files_reader] HTTP Error: {err}")
            raise
        except Exception as err:
            logging.error(f"[sharepoint_files_reader] Error in _make_ms_graph_request: {err}")
            raise

    def _get_site_id(
        self, site_domain: str, site_name: str, access_token: Optional[str] = None
    ) -> Optional[str]:
        """
        Get the Site ID from Microsoft Graph API.
        """
        # Build the correct endpoint:
        #  * If site_name is blank, "root" or "/", we’re targeting the tenant‑root site,
        #    which Graph expects without the trailing “:/sites/…:” segment.
        #  * Otherwise keep the old behaviour for regular site collections.
        if not site_name or site_name.strip().lower() in ("root", "/"):
            endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_domain}"
        else:
            endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_domain}:/sites/{site_name}:/"
        access_token = access_token or self.access_token

        try:
            logging.debug("[sharepoint_files_reader] Getting the Site ID...")
            result = self._make_ms_graph_request(endpoint, access_token)
            site_id = result.get("id")
            if site_id:
                logging.debug(f"[sharepoint_files_reader] Site ID retrieved: {site_id}")
                return site_id
        except Exception as err:
            logging.error(f"[sharepoint_files_reader] Error retrieving Site ID: {err}")
            return None

    def _get_drive_id(self, site_id: str, access_token: Optional[str] = None, drive_name: Optional[str] = None) -> str:
        """
        Get the drive ID from a Microsoft Graph site.
        """
        access_token = access_token or self.access_token
        if drive_name:
            # Fetch all drives and match by name
            url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
            try:
                json_response = self._make_ms_graph_request(url, access_token)
                drives = json_response.get("value", [])
                for drv in drives:
                    if drv.get("name", "").lower() == drive_name.lower():
                        logging.debug(f"[sharepoint_files_reader] Found drive by name: {drive_name} -> {drv.get('id')}")
                        return drv.get("id")
                logging.error(f"[sharepoint_files_reader] Drive name '{drive_name}' not found.")
                return None
            except Exception as err:
                logging.error(f"[sharepoint_files_reader] Error in get_drive_id (by name): {err}")
                return None
        else:
            # Default drive
            url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive"
            try:
                json_response = self._make_ms_graph_request(url, access_token)
                drive_id = json_response.get("id")
                logging.debug(f"[sharepoint_files_reader] Successfully retrieved drive ID: {drive_id}")
                return drive_id
            except Exception as err:
                logging.error(f"[sharepoint_files_reader] Error in get_drive_id: {err}")
                return None

    def _get_files_in_site(
        self,
        site_id: str,
        drive_id: str,
        folder_path: Optional[str] = None,
        access_token: Optional[str] = None,
        minutes_ago: Optional[int] = None,
        file_formats: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Get a list of files in a site's drive, optionally filtered by creation or last modification time and file formats.

        :param site_id: The site ID in Microsoft Graph.
        :param drive_id: The drive ID in Microsoft Graph.
        :param folder_path: Path to the folder within the drive, can include subfolders.
                The format should follow '/folder/subfolder1/subfolder2/'.For example,
                '/test/test1/test2/' to access nested folders.
        :param access_token: The access token for Microsoft Graph API authentication. If not provided, it will be fetched from self.
        :param minutes_ago: Optional integer to filter files created or updated within the specified number of minutes from now.
        :param file_formats: List of desired file formats.
        :return: A list of file details.
        :raises Exception: If there's an error in fetching file details.
        """
        if access_token is None:
            access_token = self.access_token

        # Construct the URL based on whether a folder path is provided
        if folder_path:
            url = self._format_url(site_id, drive_id, folder_path) + "children"
        else:
            url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/children"

        try:
            logging.info("[sharepoint_files_reader] Making request to Microsoft Graph API")
            json_response = self._make_ms_graph_request(url, access_token)
            files = json_response["value"]
            logging.debug("[sharepoint_files_reader] Received response from Microsoft Graph API")

            time_limit = (
                datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
                if minutes_ago is not None
                else None
            )

            filtered_files = [
                file
                for file in files
                if (
                    (
                        time_limit is None
                        or datetime.fromisoformat(
                            file["fileSystemInfo"]["createdDateTime"].rstrip("Z")
                        ).replace(tzinfo=timezone.utc)
                        >= time_limit
                        or datetime.fromisoformat(
                            file["fileSystemInfo"]["lastModifiedDateTime"].rstrip("Z")
                        ).replace(tzinfo=timezone.utc)
                        >= time_limit
                    )
                    and (
                        not file_formats
                        or any(file["name"].lower().endswith(f".{fmt.lower()}") for fmt in file_formats)
                    )
                )
            ]

            return filtered_files
        except Exception as err:
            logging.error(f"[sharepoint_files_reader] Error in get_files_in_site: {err}")
            raise

    def _get_file_permissions(
        self, site_id: str, item_id: str, access_token: Optional[str] = None
    ) -> List[Dict]:
        """
        Get the permissions of a file in a site.

        :param site_id: The site ID in Microsoft Graph.
        :param item_id: The item ID of the file in Microsoft Graph.
        :param access_token: The access token for Microsoft Graph API authentication. If not provided, it will be fetched from self.
        :return: A list of permission details.
        :raises Exception: If there's an error in fetching permission details.
        """
        if access_token is None:
            access_token = self.access_token

        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{item_id}/permissions"

        try:
            json_response = self._make_ms_graph_request(url, access_token)
            return json_response["value"]
        except Exception as err:
            logging.error(f"[sharepoint_files_reader] Error in get_file_permissions: {err}")
            raise

    @staticmethod
    def _get_read_access_entities(permissions):
        """
        Extracts user IDs and group names of entities with read access from the given permissions data.

        :param permissions: List of permission dictionaries.
        :return: List of entities (user IDs and group names/IDs) with read access.
        """
        read_access_entities = []

        for permission in permissions:
            if not isinstance(permission, dict) or "roles" not in permission:
                continue

            if any(role in permission.get("roles", []) for role in ["read", "write"]):
                # Process grantedToIdentitiesV2 for individual users
                identities_v2 = permission.get("grantedToIdentitiesV2", [])
                for identity in identities_v2:
                    user = identity.get("user", {})
                    user_id = user.get("id")
                    if user_id and user_id not in read_access_entities:
                        read_access_entities.append(user_id)

                # Process grantedToIdentities for individual users
                identities = permission.get("grantedToIdentities", [])
                for identity in identities:
                    user = identity.get("user", {})
                    user_id = user.get("id")
                    if user_id and user_id not in read_access_entities:
                        read_access_entities.append(user_id)

                # Process grantedToV2 for groups
                groups = permission.get("grantedToV2", {}).get("siteGroup", {})
                group_name = groups.get(
                    "displayName"
                )  # or groups.get('id') for group ID
                if group_name and group_name not in read_access_entities:
                    read_access_entities.append(group_name)

        return read_access_entities

    def _get_file_content_bytes(
        self,
        site_id: str,
        drive_id: str,
        folder_path: Optional[str],
        file_name: str,
        access_token: Optional[str] = None,
    ) -> Optional[bytes]:
        """
        Retrieve the content of a file as bytes from a specific site drive.

        :param site_id: The site ID in Microsoft Graph.
        :param drive_id: The drive ID in Microsoft Graph.
        :param folder_path: Path to the folder within the drive, can include subfolders.
        :param file_name: The name of the file.
        :param access_token: The access token for Microsoft Graph API authentication.
        :return: Bytes content of the file or None if there's an error.
        """
        if access_token is None:
            access_token = self.access_token

        folder_path_formatted = folder_path.rstrip("/") if folder_path else ""
        endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:{folder_path_formatted}/{file_name}:/content"

        try:
            response = requests.get(
                endpoint, headers={"Authorization": "Bearer " + access_token}
            )
            if response.status_code != 200:
                logging.error(
                    f"[sharepoint_files_reader] Failed to retrieve file content. Status code: {response.status_code}, Response: {response.text}"
                )
                return None
            return response.content
        except requests.exceptions.RequestException as req_err:
            logging.error(f"[sharepoint_files_reader] Request error: {req_err}")
            return None

    def _retrieve_file_content(
        self, site_id: str, drive_id: str, folder_path: Optional[str], file_name: str
    ) -> Optional[bytes]:
        """
        Retrieve the content of a specific file from SharePoint.

        :param site_id: SharePoint site ID.
        :param drive_id: SharePoint drive ID.
        :param folder_path: Path to the folder containing the file.
        :param file_name: Name of the file to retrieve.
        :return: Content of the file as bytes, or None if retrieval fails.
        """
        return self._get_file_content_bytes(
            site_id, drive_id, folder_path, file_name
        )

    @staticmethod
    def _extract_file_metadata(
        file_data: Dict[str, Any]
    ) -> Dict[str, Optional[Union[str, datetime]]]:
        """
        Extracts specific information from the file data.

        This function takes a dictionary containing file data and returns a new dictionary
        with specific fields: 'webUrl', 'size', 'createdBy', 'createdDateTime',
        'lastModifiedDateTime', and 'lastModifiedBy'.

        Args:
            file_data (Dict[str, Any]): The original file data.

        Returns:
            Dict[str, Optional[Union[str, datetime]]]: A dictionary with the extracted file information.
            If a field is not present in the file data, the function will return None for that field.
        """

        def format_date(date_str):
            # Append 'Z' if it's missing to indicate UTC timezone
            return date_str if date_str.endswith("Z") else f"{date_str}Z"

        return {
            "id": file_data.get("id"),
            "webUrl": file_data.get("webUrl"),
            "size": file_data.get("size"),
            "createdBy": file_data.get("createdBy", {})
            .get("user", {})
            .get("displayName"),
            "createdDateTime": format_date(
                file_data.get("fileSystemInfo", {}).get("createdDateTime", "")
            )
            if file_data.get("fileSystemInfo", {}).get("createdDateTime")
            else None,
            "lastModifiedDateTime": format_date(
                file_data.get("fileSystemInfo", {}).get("lastModifiedDateTime", "")
            )
            if file_data.get("fileSystemInfo", {}).get("lastModifiedDateTime")
            else None,
            "lastModifiedBy": file_data.get("lastModifiedBy", {})
            .get("user", {})
            .get("displayName"),
        }


    def _are_required_variables_missing(self) -> bool:
        """
        Checks if any of the required instance variables for SharePointDataExtractor are missing.

        This function checks the following instance variables: 'tenant_id', 'client_id',
        'client_secret', 'graph_uri', and 'authority'. If any of these variables are not set,
        the function logs an error message and returns True.

        :return: True if any of the required instance variables are missing, False otherwise.
        """
        required_vars = {
            "tenant_id": self.tenant_id,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "graph_uri": self.graph_uri,
            "authority": self.authority,
        }
        missing_vars = [var_name for var_name, var in required_vars.items() if not var]
        if missing_vars:
            logging.error(
                f"[sharepoint_files_reader] Required instance variables for SharePointDataExtractor are not set: {', '.join(missing_vars)}. Please load load_environment_variables_from_env_file or set them manually."
            )
            return True
        return False

    def _get_site_and_drive_ids(
        self, site_domain: str, site_name: str, drive_name: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Retrieves the site ID and drive ID for a given site domain and site name.

        :param site_domain: The domain of the site.
        :param site_name: The name of the site.
        :param drive_name: Optional; the name of the drive to retrieve files from. If not provided, the default drive will be used.
        :return: A tuple containing the site ID and drive ID, or (None, None) if either ID could not be retrieved.
        """
        site_id = self._get_site_id(site_domain, site_name)
        if not site_id:
            logging.error("[sharepoint_files_reader] Failed to retrieve site_id")
            return None, None

        drive_id = self._get_drive_id(site_id, drive_name=drive_name)
        if not drive_id:
            logging.error("[sharepoint_files_reader] Failed to retrieve drive ID")
            return None, None

        return site_id, drive_id

    def _get_files(
        self,
        site_id: str,
        drive_id: str,
        folder_path: Optional[str],
        minutes_ago: Optional[int],
        file_formats: Optional[List[str]],
    ) -> List[Dict]:
        """
        Retrieves the files in a site drive.

        :param site_id: The site ID in Microsoft Graph.
        :param drive_id: The drive ID in Microsoft Graph.
        :param folder_path: Optional path to the folder within the drive, can include subfolders.
        :param minutes_ago: Optional integer to filter files created or updated within the specified number of minutes from now.
        :param file_formats: List of desired file formats.
        :return: A list of file details.
        """
        files = self._get_files_in_site(
            site_id=site_id,
            drive_id=drive_id,
            folder_path=folder_path,
            minutes_ago=minutes_ago,
            file_formats=file_formats,
        )
        return files

    def _process_files(
        self,
        site_id: str,
        drive_id: str,
        folder_path: Optional[str],
        file_names: Optional[Union[str, List[str]]],
        files: List[Dict],
        file_formats: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """Processes the files in a site drive.

        :param site_id: The site ID in Microsoft Graph.
        :param drive_id: The drive ID in Microsoft Graph.
        :param folder_path: Optional path to the folder within the drive, can include subfolders.
        :param file_names: The name(s) of specific files to filter. Can be a string or a list of strings.
        :param files: List of files to process.
        :param file_formats: List of desired file formats.
        :return: A list of dictionaries, each mapping file names to their content and metadata.
        """
        file_contents = []

        # Handle both string and list for file_names
        if isinstance(file_names, str):
            file_names = [file_names]

        # Filter files based on the given file_names
        if file_names:
            files = [file for file in files if file.get("name") in file_names]
            if len(files) == 0:
                logging.error("[sharepoint_files_reader] No matching files found")
                return []

        for file in files:
            file_name = file.get("name")
            if file_name and self._is_file_format_valid(file_name, file_formats):
                metadata = self._extract_file_metadata(file)
                content = self._retrieve_file_content(
                    site_id, drive_id, folder_path, file_name
                )
                users_by_role = self._get_read_access_entities(
                    self._get_file_permissions(site_id, file["id"])
                )
                file_content = {
                    "content": content,
                    **self._format_metadata(metadata, file_name, users_by_role),
                }
                file_contents.append(file_content)

        return file_contents

    def _is_file_format_valid(
        self, file_name: str, file_formats: Optional[List[str]]
    ) -> bool:
        """
        Checks if the format of a file is valid.

        :param file_name: The name of the file.
        :param file_formats: List of desired file formats.
        :return: True if the file format is valid, False otherwise.
        """
        return "." in file_name and (
            not file_formats
            or any(file_name.lower().endswith(f".{fmt.lower()}") for fmt in file_formats)
        )

    def _format_metadata(
        self,
        metadata: Dict,
        file_name: str,
        users_by_role: Dict,
    ) -> Dict:
        """
        Format and return file metadata.

        :param metadata: Dictionary of file metadata.
        :param file_name: Name of the file.
        :param users_by_role: Dictionary of users grouped by their role.
        :return: Formatted metadata as a dictionary.
        """
        formatted_metadata = {
            "id": metadata["id"],
            "source": metadata["webUrl"],
            "name": file_name,
            "size": metadata["size"],
            "created_by": metadata["createdBy"],
            "created_datetime": metadata["createdDateTime"],
            "last_modified_datetime": metadata["lastModifiedDateTime"],
            "last_modified_by": metadata["lastModifiedBy"],
            "read_access_entity": users_by_role,
        }
        return formatted_metadata

    def interactive_login(self):
        """
        Initiates a browser-based interactive login to acquire a Microsoft Graph API token for the user.
        Sets self.access_token if successful.
        """
        import msal
        # Try both naming conventions for environment variables
        client_id = self.client_id or os.getenv("SHAREPOINT_CLIENT_ID") or os.getenv("AZURE_CLIENT_ID")
        tenant_id = self.tenant_id or os.getenv("AZURE_TENANT_ID") or os.getenv("SHAREPOINT_TENANT_ID")
        
        authority = f"https://login.microsoftonline.com/{tenant_id}" if tenant_id else None
        scope = ["https://graph.microsoft.com/.default"]
        
        if not client_id or not tenant_id:
            logging.error(f"[sharepoint_files_reader] Missing client_id or tenant_id for interactive login. client_id={bool(client_id)}, tenant_id={bool(tenant_id)}")
            return None
            
        logging.info(f"[sharepoint_files_reader] Starting interactive login with client_id={client_id[:5]}...")
        
        app = msal.PublicClientApplication(client_id, authority=authority)
        try:
            # Try silent token acquisition first
            accounts = app.get_accounts()
            if accounts:
                silent_result = app.acquire_token_silent(scope, account=accounts[0])
                if silent_result:
                    logging.info("[sharepoint_files_reader] Token acquired silently from cache")
                    self.access_token = silent_result["access_token"]
                    return self.access_token
                    
            # No cached token - try interactive login
            logging.info("[sharepoint_files_reader] No cached token, launching browser for interactive login...")
            result = app.acquire_token_interactive(scopes=scope)
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                logging.info("[sharepoint_files_reader] Interactive login succeeded. Access token acquired.")
                return self.access_token
            else:
                error_msg = result.get("error_description", "Unknown error")
                logging.error(f"[sharepoint_files_reader] Interactive login failed: {error_msg}")
                return None
        except Exception as e:
            logging.error(f"[sharepoint_files_reader] Exception during interactive login: {str(e)}")
            return None

    def _log_auth_diagnostic(self):
        """Log diagnostic information about authentication configuration."""
        import os
        import logging
        
        # Print the environment variables related to SharePoint auth
        auth_vars = {
            "AZURE_TENANT_ID": os.getenv("AZURE_TENANT_ID", ""),
            "SHAREPOINT_TENANT_ID": os.getenv("SHAREPOINT_TENANT_ID", ""),
            "SHAREPOINT_CLIENT_ID": os.getenv("SHAREPOINT_CLIENT_ID", ""),
            "AZURE_CLIENT_ID": os.getenv("AZURE_CLIENT_ID", ""),
            "AGENTIC_APP_SPN_CERT_PATH": os.getenv("AGENTIC_APP_SPN_CERT_PATH", ""),
            "CERT EXISTS": os.path.exists(os.getenv("AGENTIC_APP_SPN_CERT_PATH", "")) if os.getenv("AGENTIC_APP_SPN_CERT_PATH") else False,
            "SHAREPOINT_SITE_DOMAIN": os.getenv("SHAREPOINT_SITE_DOMAIN", "")
        }
        
        logging.info("SharePoint Authentication Configuration:")
        for var, value in auth_vars.items():
            # Mask sensitive values in logs
            if var != "CERT EXISTS" and value:
                display_val = value[:5] + "..." if len(value) > 8 else "[SET]"
                logging.info(f"  {var}: {display_val}")
            else:
                logging.info(f"  {var}: {value}")
        
        # Log which authentication method will be used
        cert_path = os.getenv("AGENTIC_APP_SPN_CERT_PATH", "")
        cert_exists = cert_path and os.path.exists(cert_path)
        
        if cert_exists and os.getenv("AGENTIC_APP_SPN_CERT_PASSWORD"):
            logging.info("Authentication method: Certificate-based service principal")
        elif os.getenv("SHAREPOINT_CLIENT_SECRET") or os.getenv("SHAREPOINT_CLIENT_SECRET_VALUE"):
            logging.info("Authentication method: Client secret service principal")
        else:
            logging.info("Authentication method: Interactive browser login (fallback)")
