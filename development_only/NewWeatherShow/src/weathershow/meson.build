configurationData = configuration_data()
configurationData.set('PACKAGE_NAME', meson.project_name())
configurationData.set('LOCALE_DIR', LOCALE_DIR)
configure_file(input: 'config.h.in', output: 'config.h', configuration: configurationData)

install_data('WeatherShow.plugin', install_dir: LIB_INSTALL_DIR)

WeatherShowSources = [
'WeatherShow.vala'
]

WeatherShowDependencies = [
dependency('gtk+-3.0'), 
dependency('budgie-1.0'),
dependency('gee-0.8'),
dependency('libsoup-2.4'),
dependency('libpeas-gtk-1.0'),
dependency('json-glib-1.0'),
dependency('libpeas-gtk-1.0'),
meson.get_compiler('c').find_library('m', required: false)
]

WeatherShowValaArgs = [
'--pkg=config', 
'--vapidir=' + VAPI_DIR, 
'--target-glib=2.38',
]

WeatherShowCArgs = [
'-include', 
'config.h',
'-lm'
]

shared_library(
    'weathershow', 
    WeatherShowSources, 
    dependencies: WeatherShowDependencies, 
    vala_args: WeatherShowValaArgs, 
    c_args: WeatherShowCArgs, 
    install: true, 
    install_dir: LIB_INSTALL_DIR
)




