; Bridgiron Installer Script
; Inno Setup 6.x

#define MyAppName "Bridgiron"
#define MyAppVersion "1.13"
#define MyAppPublisher "らいお"
#define MyAppExeName "Bridgiron.exe"

[Setup]
AppId={{36A9FED9-52DD-4743-8FF4-104E85A39536}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=Bridgiron_Setup_v{#MyAppVersion}
SetupIconFile=..\images\Icon05.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"; LicenseFile: "..\\_DOC\\license_ja.txt"
Name: "english"; MessagesFile: "compiler:Default.isl"; LicenseFile: "..\\_DOC\\license_en.txt"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "..\dist\Bridgiron.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\\_Config\\keywords.txt"; DestDir: "{app}\_Config"; Flags: ignoreversion
Source: "..\\_Config\\phrases.txt"; DestDir: "{app}\_Config"; Flags: ignoreversion
Source: "..\\_Config\\delimiters.txt"; DestDir: "{app}\_Config"; Flags: ignoreversion
Source: "..\\_DOC\\Readme.html"; DestDir: "{app}\_DOC"; Flags: ignoreversion
Source: "..\\_DOC\\Readme_en.html"; DestDir: "{app}\_DOC"; Flags: ignoreversion
Source: "..\\_DOC\\Bridgiron_Girl.png"; DestDir: "{app}\_DOC"; Flags: ignoreversion
Source: "..\\images\\*"; DestDir: "{app}\\images"; Flags: ignoreversion recursesubdirs createallsubdirs
; ブックマークレットテンプレート
Source: "..\\src\\js\\bookmarklet_gpt_extract.js"; DestDir: "{app}\\src\\js"; Flags: ignoreversion
; 注意: settings.txt は [Code] セクションで言語・プロジェクトパスを反映して生成

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Readme表示（デフォルトON）
Filename: "{app}\_DOC\Readme.html"; Description: "Readmeを開く / Open Readme"; Flags: shellexec postinstall skipifsilent
; アプリ起動（デフォルトOFF）
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent unchecked

[Code]
var
  ProjectPathPage: TInputDirWizardPage;

// カスタムページの初期化
procedure InitializeWizard;
begin
  // プロジェクトパス入力ページを追加（インストール先選択の後）
  ProjectPathPage := CreateInputDirPage(wpSelectDir,
    'Claude Code Project Path',
    'Please specify the project folder for Claude Code.',
    'Select the folder where your Claude Code project is located:',
    False, '');
  ProjectPathPage.Add('');
  ProjectPathPage.Values[0] := 'C:\Hoge\Piyo';

  // 日本語の場合はラベルを変更
  if ActiveLanguage = 'japanese' then
  begin
    ProjectPathPage.Caption := 'Claude Code プロジェクトパス';
    ProjectPathPage.Description := 'Claude Codeで使用するプロジェクトフォルダを指定してください。';
  end;
end;

// インストール時に選択した言語とプロジェクトパスを settings.txt に反映
// settings.txt は AppData に保存（Program Files の権限問題を回避）
procedure CurStepChanged(CurStep: TSetupStep);
var
  SettingsDir: string;
  SettingsFile: string;
  Lang: string;
  ProjectPath: string;
  CcPrefix: string;
  UTF8BOM: AnsiString;
begin
  if CurStep = ssPostInstall then
  begin
    // AppData に設定ディレクトリを作成
    SettingsDir := ExpandConstant('{userappdata}\Bridgiron');
    ForceDirectories(SettingsDir);
    SettingsFile := SettingsDir + '\settings.txt';

    ProjectPath := ProjectPathPage.Values[0];

    // 言語設定を決定
    if ActiveLanguage = 'japanese' then
    begin
      Lang := 'ja';
      CcPrefix := 'Claude Codeの報告は下記。\n';
    end
    else
    begin
      Lang := 'en';
      CcPrefix := 'Claude Code''s report is below.\n';
    end;

    // UTF-8 BOM (EF BB BF)
    UTF8BOM := #$EF#$BB#$BF;

	// settings.txt を AppData に作成
    SaveStringToFile(SettingsFile,
                                   'language=' + Lang + #13#10 +
                                   'bookmarklet_title=CopyPrompt GPT2CC' + #13#10 +
                                   'project_path=' + ProjectPath + #13#10 +
                                   'cc_prefix=' + CcPrefix + #13#10 +
                                   'mini_window_position=cli_bottom_left' + #13#10 +
                                   'first_run=1' + #13#10, False);
  end;
end;
