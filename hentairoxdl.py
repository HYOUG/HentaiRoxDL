#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# script by "HYOUG"

from argparse import ArgumentParser
from os import listdir, makedirs, remove
from os.path import basename, exists, join
from threading import Thread
from zipfile import ZIP_DEFLATED, ZipFile
from bs4 import BeautifulSoup
from requests import get
from tqdm import tqdm
from colorama import Fore
from modules.errors import *


metadata_dict = {
    "parodies": [],
    "characters": [],
    "tags": [],
    "artists": [],
    "groups": [],
    "languages": [],
    "category": []
}
IMAGE_EXTENSIONS = ["jpg", "png", "gif"]
FORBIDDEN_CHARS = ["<", ">", ":", "\"", "/", "\\", "|", "?", "*"]
NONE_TYPE = type(None)


def dl_gallery(gallery_url:str, output:str, filename:str, pages:list,
               archive: str or NONE_TYPE, threads:int, metadata:bool) -> None:
    """
    Download a given Hentai Rox Gallery

    Parameters
    ----------
    gallery_url : str
        URL from the targeted gallery page
    output : str
        Output path for the downloaded pictures, by default "./downloads"
    filename : str
        Filename model for the downloaded pictures, by default "{gallery_id}_{page_num}}"
    pages : list
        Minimum and maximum page indexed for the downloaded pictures, by default [0, -1]
    archive : str or NONE_TYPE
        Archive the downloaded pictures if a name is given, by default None
    threads : int
        Number of workers downloading pictures in parallel, by default 1
    metadata : bool
        Save gallery metadata in a file (#metadata.txt), by default False

    Raises
    ------
    InvalidURL
        The gallery URL given is invalid
    """

    assert isinstance(gallery_url, str), f"Invalid data format given for the \"gallery_url\" argument : {type(gallery_url)} (instead of str)"
    assert isinstance(output, str), f"Invalid data format given for the \"output\" argument : {type(output)} (instead of str)"
    assert isinstance(filename, str), f"Invalid data format given for the \"_filename\" argument : {type(filename)} (instead of str)"
    assert isinstance(pages, list), f"Invalid data format given for the \"pages\" argument : {type(pages)} (instead of list)"
    assert isinstance(archive, (NONE_TYPE, str)), f"Invalid data format given for the \"archive\" argument : {type(archive)} (instead of NONE_TYPE or str)"
    assert isinstance(threads, int), f"Invalid data format given for the \"threads\" argument : {type(threads)} (instead of int)"
    assert isinstance(metadata, bool), f"Invalid data format given for the \"metadata\" argument : {type(metadata)} (instead of bool)"
    assert gallery_url.startswith("https://hentairox.com/gallery/"), f"Invalid gallery URL given : {gallery_url}"


    gallery_id = [i for i in gallery_url.split("/") if i != ""][-1]
    threads_list = []
    bars_list = []

    if not exists(output):
        makedirs(output)

    response = get(gallery_url)
    if response.status_code == 404:
        raise InvalidURL(gallery_url)
    soup = BeautifulSoup(response.content, "html.parser")

    gallery_name = soup.find("h1").string
    metadata_tags = soup.find_all("span", {"class": "item_name"})
    for metadata_tag in metadata_tags:
        metadata_type = metadata_tag.parent["href"]
        if metadata_type.startswith("/parody"):
            metadata_dict["parodies"].append(metadata_tag.contents[0])
        elif metadata_type.startswith("/character"):
            metadata_dict["characters"].append(metadata_tag.contents[0])
        elif metadata_type.startswith("/tag"):
            metadata_dict["tags"].append(metadata_tag.contents[0])
        elif metadata_type.startswith("/artist"):
            metadata_dict["artists"].append(metadata_tag.contents[0])
        elif metadata_type.startswith("/group"):
            metadata_dict["groups"].append(metadata_tag.contents[0])
        elif metadata_type.startswith("/language"):
            metadata_dict["languages"].append(metadata_tag.contents[0])
        elif metadata_type.startswith("/category"):
            metadata_dict["category"].append(metadata_tag.contents[0])

    page_num_node = soup.find("li", {"class": "pages"})
    pages_num = int(page_num_node.string.split(" ")[0])
    first_img = soup.find("img", {"class": "lazy preloader"})
    pattern = "/".join(first_img["data-src"].split("/")[:-1]) + "/"

    print(f"\nDownloading : {Fore.LIGHTBLUE_EX}{gallery_name}{Fore.RESET}\n")

    if metadata:
        fp = join(output, "#metadata.txt")
        f = open(fp, "w", encoding="utf-8")
        f.write(f"Gallery name: {gallery_name}\n")
        f.write(f"URL: {gallery_url}\n")
        f.write(f"Pages: {pages_num}\n\n")
        f.write(f"Metadata:\n")
        for (category, tag_list) in metadata_dict.items():
            if len(tag_list) > 0:
                f.write(f"* {category}: {', '.join(tag_list)}\n")
        f.close()

    if archive is not None:
        if f"{archive}.zip" not in listdir(output):
            zf = ZipFile(join(output, f"{archive}.zip"), "w", ZIP_DEFLATED)
        else:
            zf = ZipFile(join(output, f"{archive}.zip"), "a", ZIP_DEFLATED)
        if metadata:
            zf.write(fp, basename(fp)) 
            remove(fp)

    p_start = list(range(pages_num)).index(list(range(pages_num))[pages[0]])
    p_end = list(range(pages_num)).index(list(range(pages_num))[pages[1]])
    p_len = p_end - p_start
    

    def dl_pages(t_start, t_end, t_num):
        for i in range(t_start, t_end):
            for ext in IMAGE_EXTENSIONS:
                response = get(f"{pattern}/{i+1}.{ext}")
                if response.status_code == 200:
                    formatfound = True
                    im_ext = ext
                    break
                formatfound = False
            if formatfound:
                model_vars = {
                    "{gallery_name}": gallery_name,
                    "{gallery_id}": gallery_id,
                    "{page_num}": str(i),
                    "{pages_num}": str((t_end-1)-t_start)}
                parsed_filename = filename
                for (var_name, var_value) in model_vars.items():
                    parsed_filename = parsed_filename.replace(var_name, var_value)
                fp = join(output, f"{parsed_filename}.{im_ext}")
                f = open(fp, "wb")
                f.write(response.content)
                f.close()
                if archive is not None:
                    zf.write(fp, basename(fp))
                    remove(fp)
                    zf.close()
            bars_list[t_num].update()


    for i in range(threads):
        if i != threads-1:
            t_start = p_start + ((p_len//threads) * i)
            t_end = p_start + ((p_len//threads) * (i+1))
        else:
            t_start = p_start + ((p_len//threads) * i)
            t_end = p_start + ((p_len//threads) * (i+1)) + (p_len % threads)
        bar = tqdm(
            iterable=range(t_start, t_end),
            total=t_end-t_start,
            bar_format="Thread tn : |{bar:30}| [{n_fmt}/{total_fmt}] ~ {percentage:.0f}%".replace("tn", str(i+1)),
            ascii=".▌█",
            position=i)
        bars_list.append(bar)
        thread = Thread(target=dl_pages, args=(t_start, t_end, i))
        threads_list.append(thread)
        threads_list[-1].start()
    [thread.join() for thread in threads_list]


def main():
    parser = ArgumentParser(prog="HentaiRoxDL.py",
                            epilog="Made with <3 by HYOUG")
    parser.add_argument("gallery_url",
                        nargs="+",
                        help="The URL from the targeted gallery page",
                        metavar="GALLERY_URL")
    parser.add_argument("-o", "--output",
                        default="./downloads",
                        help="Path for the output for the downloaded content",
                        metavar="PATH")
    parser.add_argument("-f", "--filename",
                        default="{gallery_id}_{page_num}",
                        help="Filename model given to the downloaded pictures",
                        metavar="FILENAME_MODEL")
    parser.add_argument("-p", "--pages",
                        nargs=2,
                        default=[0, -1],
                        type=int,
                        help="Specific page indexes to download",
                        metavar=("START_INDEX", "STOP_INDEX"))
    parser.add_argument("-a", "--archive",
                        default=None,
                        help="Archive the downloaded pictures in a zip file with the given name",
                        metavar="ARCHIVE_NAME")
    parser.add_argument("-t", "--threads",
                        default=1,
                        type=int,
                        help="Downloads the targeted pictures in parallel with N threads. N being the provided argument",
                        metavar="N_WORKERS")
    parser.add_argument("-m", "--metadata",
                        action="store_true",
                        default=False,
                        help="Save the gallery's metadata into a file (#metadata.txt)")          
  
    args = parser.parse_args()
    for url in args.gallery_url:
        dl_gallery(url, args.output, args.filename, args.pages, args.archive, args.threads, args.metadata)


if __name__ == "__main__":
    main()
