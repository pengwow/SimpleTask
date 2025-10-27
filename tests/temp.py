from nicegui import ui
project = {
    'uploaded_file': None,
    'git_url': '',
    'git_branch': 'master',
    'git_username': '',
    'git_password': ''
}
with ui.dialog() as dialog, ui.card().classes('w-full'):
    with ui.tabs().classes('w-full flex justify-between') as tabs:
        git_tab = ui.tab('git', label='Git仓库', icon='fork_left').classes('w-1/2 text-center')
        zip_tab = ui.tab('zip', label='ZIP上传', icon='folder_zip').classes('w-1/2 text-center')
    with ui.tab_panels(tabs, value=git_tab).classes('w-full'):
        with ui.tab_panel(zip_tab):
            print('zip_tab')
            # ui.label('First tab')
            # ZIP上传区域
            with ui.card().classes('border-dashed border-2 border-gray-300 p-8 text-center rounded-lg'):
                ui.icon('upload').classes('text-4xl text-gray-400 mb-2')
                ui.label('拖拽ZIP文件到此，或点击选择').classes('mb-2')
                upload = ui.upload(on_upload=lambda e: handle_file_upload(e, project))
                upload.props('accept=".zip" label="点击上传"')
                if project['uploaded_file']:
                    ui.label(f'已选择文件: {project["uploaded_file"]}').classes('text-green-600 mt-2')
        with ui.tab_panel(git_tab):
            print('git_tab')
            ui.label('Git仓库地址 *').classes('text-sm font-medium')
            ui.input().classes('w-full').bind_value(project, 'git_url')

            ui.label('分支').classes('text-sm font-medium')
            ui.input().classes('w-full').bind_value(project, 'git_branch')

            ui.label('用户名').classes('text-sm font-medium')
            ui.input().classes('w-full').props('placeholder="Git用户名 (可选)"').bind_value(project, 'git_username')

            ui.label('密码').classes('text-sm font-medium')
            ui.input(password=True).classes('w-full').props('placeholder="Git密码 (可选)"').bind_value(project, 'git_password')
            ui.label('请输入Git仓库的访问凭证').classes('text-xs text-gray-500 mt-1')
dialog.open()
ui.run()