"""
Tools used for pre-processing data.




At the moment there is nothing here, as external data repositories,
such as Nemosis, Nemed, etc. are run externally.
Some dependancies issues with nemed stopped me to finish it.
So far, the codes run without problems with the existing data.

"""

import requests
import sys
import os
from os.path import isfile

from tm_solarshift.constants import DIRECTORY

class MERRA2():

    # Set the URL string to point to a specific data URL. Some generic examples are:
    #   https://servername/data/path/file
    #   https://servername/opendap/path/file[.format[?subset]]
    #   https://servername/daac-bin/OTF/HTTP_services.cgi?KEYWORD=value[&KEYWORD=value]

    FLDR_DATA_RAW = os.path.join(DIRECTORY.DIR_DATA["weather"],"merra2_raw")
    FLDR_DATA_PROC = os.path.join(DIRECTORY.DIR_DATA["weather"],"merra2_processed")

    @classmethod
    def downloader_pydap(cls, dataset: str, file_path: str, verbose: bool = False) -> None: 
        from pydap.client import open_url
        from pydap.cas.urs import setup_session

        dataset_url = 'https://servername/opendap/path/file[.format[?subset]]'

        username = 'david.saldivia23'
        password = 'daVinci72315'

        list_files = open(file_path, 'r')
        lines = list_files.readlines()
        for line in lines:
            URL = line
            pass
            try:
                session = setup_session(username, password, check_url=dataset_url)
                dataset = open_url(dataset_url, session=session)
                print(dataset)
            except AttributeError as e:
                print('Error:', e)
                print('Please verify that the dataset URL points to an OPeNDAP server, the OPeNDAP server is accessible, or that your username and password are correct.')
            
        return
    
    @classmethod
    def downloader_requests(cls, dataset: str, file_path: str, verbose: bool = False) -> None:                
        list_files = open(file_path, 'r')
        if dataset == "slv":
            keyword1 = 'SERVICE'
            keyword2 = 'DATASET_VERSION'
        elif dataset == "rad":
            keyword1 = 'LABEL'
            keyword2 = 'FORMAT'

        lines = list_files.readlines()
        # for line in lines:
        #     URL = line
        #     print(URL)
        # print()
        i = 0
        for line in lines:
            URL = line[:-2]
            FILENAME = os.path.join(cls.FLDR_DATA_RAW, f"file_{i:0d}.nc4")
            if not(isfile(FILENAME)):
                result = requests.get(URL)
                try:
                    result.raise_for_status()
                    f = open(FILENAME,'wb')
                    f.write(result.content)
                    f.close()
                    if verbose:
                        print('contents of URL written to '+FILENAME)
                except:
                    if verbose:
                        print('requests.get() returned an error code '+str(result.status_code))
                
                with open(os.path.join(cls.FLDR_DATA_RAW,'Failed_files.txt'), 'a+') as f:
                    f.write(URL)
        if verbose:
            print(f"Downloading files in {file_path} is finished.")

    @classmethod
    def downloader_xarray(cls, dataset: str, file_path: str, verbose: bool = False) -> None:        
        
        import xarray as xr
        list_files = open(file_path, 'r')
        lines = list_files.readlines()
        
        i=0
        for line in lines:
            URL = line[:-2]
            FILENAME = os.path.join(cls.FLDR_DATA_RAW, f"file_{i:0d}.nc4")
            i+=1
            if not(isfile(FILENAME)):
                try:
                    ds = xr.open_dataset(URL)
                    ds.to_netcdf(FILENAME)
                    if verbose:
                        print('contents of URL written to '+FILENAME)

                except:
                    if verbose:
                        print('xarray couldnt read the link')
                
                    with open(os.path.join(cls.FLDR_DATA_RAW,'Failed_files.txt'), 'a+') as f:
                        f.write(line)
        if verbose:
            print(f"Downloading files in {file_path} is finished.")

        return
    
    @staticmethod
    def credentials():
        from subprocess import Popen
        from getpass import getpass
        import platform
        import os
        import shutil

        urs = 'urs.earthdata.nasa.gov'    # Earthdata URL to call for authentication
        prompts = ['Enter NASA Earthdata Login Username \n(or create an account at urs.earthdata.nasa.gov): ',
                'Enter NASA Earthdata Login Password: ']

        homeDir = os.path.expanduser("~") + os.sep

        with open(homeDir + '.netrc', 'w') as file:
            file.write('machine {} login {} password {}'.format(urs, getpass(prompt=prompts[0]), getpass(prompt=prompts[1])))
            file.close()
        with open(homeDir + '.urs_cookies', 'w') as file:
            file.write('')
            file.close()
        with open(homeDir + '.dodsrc', 'w') as file:
            file.write('HTTP.COOKIEJAR={}.urs_cookies\n'.format(homeDir))
            file.write('HTTP.NETRC={}.netrc'.format(homeDir))
            file.close()

        print('Saved .netrc, .urs_cookies, and .dodsrc to:', homeDir)

        # Set appropriate permissions for Linux/macOS
        if platform.system() != "Windows":
            Popen('chmod og-rw ~/.netrc', shell=True)
        else:
            # Copy dodsrc to working directory in Windows  
            shutil.copy2(homeDir + '.dodsrc', os.getcwd())
            print('Copied .dodsrc to:', os.getcwd())

    @classmethod
    def processing(cls, fldr_path : str, verbose: bool = True):
        
        import xarray as xr

        tz = 'Australia/Brisbane'
        list_files = os.listdir(fldr_path)
        list_files.sort()
        list_slv =  [x for x in list_files if ('slv') in x]
        list_rad =  [x for x in list_files if ('rad') in x]

        data = xr.Dataset()
        for i in range(len(list_slv)):
                    
            file_rad = os.path.join(fldr_path,list_rad[i])
            data_rad = xr.open_dataset(file_rad)
            file_slv = os.path.join(fldr_path,list_slv[i])
            data_slv = xr.open_dataset(file_slv)
            data_slv = data_slv.where(data_slv.lon>=110., drop=True).assign(data_rad)
            data = data.merge(data_slv)
            if verbose and i%10==0:
                print('{:d} days alread processed'.format(i+1))
        print(data)

        data['WS'] = (data['V2M']**2+data['U2M']**2)**0.5
        data  = data.drop_vars(['V2M','U2M'])
        data = data.rename({"SWGDN":"GHI", "T2M":"Temp_Amb"})
        file_out = os.path.join(MERRA2.FLDR_DATA_PROC, "MERRA2_Processed_2023.nc")
        data.to_netcdf(file_out)

        return

#--------------
def main():

    # MERRA2.credentials()

    if True:   
        fldr_path = os.path.join(MERRA2.FLDR_DATA_RAW, '2023')
        MERRA2.processing(fldr_path)

    if False:
        dataset = "slv"
        file_path = os.path.join(MERRA2.FLDR_DATA_RAW, 'subset_M2T1NXSLV_5.12.4_20240220_181348_.txt')
        MERRA2.downloader_requests(dataset, file_path, verbose = True)
    
    if False:
        dataset = "slv"
        file_path = os.path.join(MERRA2.FLDR_DATA_RAW, 'subset_M2T1NXSLV_5.12.4_20240220_183505_.txt')
        MERRA2.downloader_pydap(dataset, file_path, verbose = True)
    
    if False:
        dataset = "slv"
        file_path = os.path.join(MERRA2.FLDR_DATA_RAW, 'subset_M2T1NXSLV_5.12.4_20240220_183505_.txt')
        MERRA2.downloader_xarray(dataset, file_path)


#----------------
if __name__ == "__main__":
    main()
    pass
