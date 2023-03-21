from configparser import ConfigParser
from json import loads as jsonloads
from re import escape as rescape
from os import path as ospath
from asyncio.subprocess import PIPE, create_subprocess_exec
from bot import GLOBAL_EXTENSION_FILTER, LOGGER, OWNER_ID, config_dict, remotes_data
from bot.helper.ext_utils.exceptions import NotRclonePathFound
from bot.helper.ext_utils.filters import CustomFilters
from bot.helper.ext_utils.message_utils import editMessage, sendMarkup, sendMessage
from bot.helper.ext_utils.button_build import ButtonMaker
from bot.helper.ext_utils.rclone_data_holder import get_rclone_data, update_rclone_data
from asyncio.subprocess import PIPE
from json import loads as jsonloads
from configparser import ConfigParser            
            


async def is_remote_selected(user_id, message):
    if config_dict['MULTI_RCLONE_CONFIG'] or CustomFilters._owner_query(user_id):
        if (DEFAULT_OWNER_REMOTE:= config_dict['DEFAULT_OWNER_REMOTE']) and user_id == OWNER_ID:
            update_rclone_data("CLOUDSEL_REMOTE", DEFAULT_OWNER_REMOTE, user_id)
            return True
        elif get_rclone_data("CLOUDSEL_REMOTE", user_id) or len(remotes_data) > 0:
            return True
        else:
            await sendMessage("Select a cloud first, use /cloudselect", message)
            return False
    else:
        return True

async def is_rclone_config(user_id, message, isLeech=False):
    if config_dict['MULTI_RCLONE_CONFIG'] or CustomFilters._owner_query(user_id):
        path= ospath.join("users", f'{user_id}', "rclone.conf")
        msg= "Send a rclone config file, use /botfiles command"
    else:
        path= ospath.join("users", "grclone", "rclone.conf")
        msg= "Global rclone not found"
    if ospath.exists(path):
        return True
    else:
        if isLeech:
            return True
        else:
            await sendMessage(msg, message)
            return False    

def get_rclone_config(user_id):
    if config_dict['MULTI_RCLONE_CONFIG'] or CustomFilters._owner_query(user_id):
        rc_path = ospath.join("users", f"{user_id}" , "rclone.conf")
    else:
        rc_path = ospath.join("users", "grclone", "rclone.conf")      
    if ospath.exists(rc_path): 
        return rc_path 
    else:
        raise NotRclonePathFound(f"ERROR: Rclone path not found")

async def list_remotes_ml(message, rclone_remote, base_dir, callback, edit=False):
    user_id= message.from_user.id
    buttons = ButtonMaker()
    path= get_rclone_config(user_id)
    conf = ConfigParser()
    conf.read(path)
    for remote in conf.sections():
        prev = ""
        if remote == get_rclone_data("CLOUDSEL_REMOTE", user_id):
            prev = "✅"
        buttons.cb_buildbutton(f"{prev} 📁 {remote}", f"{callback}^remote^{remote}^{message.id}")
    buttons.cb_buildbutton("✘ Close Menu", f"{callback}^close^{message.id}", 'footer')
    msg= f"Select cloud where you want to upload file\n\n<b>Path:</b><code>{rclone_remote}:{base_dir}</code>" 
    if edit:
        await editMessage(msg, message, reply_markup= buttons.build_menu(2))
    else:
        await sendMarkup(msg, message, reply_markup= buttons.build_menu(2))

async def setRcloneFlags(cmd, type):
    ext = '*.{' + ','.join(GLOBAL_EXTENSION_FILTER) + '}'
    cmd.extend(('--exclude', ext))
    if type == "copy":
        if flags := config_dict.get('RCLONE_COPY_FLAGS'):
            append_flags(flags,cmd)
    elif type == "upload":
        if flags := config_dict.get('RCLONE_UPLOAD_FLAGS'):
            append_flags(flags,cmd)
    elif type == "download":
        if flags := config_dict.get('RCLONE_DOWNLOAD_FLAGS'):
            append_flags(flags,cmd)
           
def append_flags(flags, cmd):
    rcflags = flags.split(',')
    for flag in rcflags:
        if ":" in flag:
            key, value = flag.split(":")
            cmd.extend((key, value))
        elif len(flag) > 0:
            cmd.append(flag)

async def get_gdlink(remote, base, name, conf, type, buttons):
    if type == "Folder":
        s_name = rescape(name.replace(".", ""))
        cmd = ["rclone", "lsjson", f'--config={conf}', f"{remote}:{base}", "--dirs-only", "-f", f"+ {s_name}/", "-f", "- *"]
    else:
        s_name = rescape(name)
        cmd = ["rclone", "lsjson", f'--config={conf}', f"{remote}:{base}", "--files-only", "-f", f"+ {s_name}", "-f", "- *"]
    
    process = await create_subprocess_exec(*cmd,stdout= PIPE,stderr= PIPE)
    stdout, stderr = await process.communicate()
    return_code = await process.wait()
    stdout = stdout.decode().strip()
    if return_code != 0:
        err = stderr.decode().strip()
        LOGGER.error(f'Error: {err}') 
        return
    
    try:
        data = jsonloads(stdout)
        id = data[0]["ID"]
        if type == "Folder":
            link = f'https://drive.google.com/drive/folders/{id}'
            buttons.url_buildbutton('Cloud Link 🔗', link)
        else:
            link = f'https://drive.google.com/uc?id={id}&export=download'
            buttons.url_buildbutton('Cloud Link 🔗', link)
    except Exception:
        link = 'https://drive.google.com/file/d/err/view'
        LOGGER.error("Error while getting id")