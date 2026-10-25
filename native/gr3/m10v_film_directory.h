/* Generated from web/gr3/film-directory.json. Display order is not identity. */
#ifndef M10V_FILM_DIRECTORY_H
#define M10V_FILM_DIRECTORY_H
#include <stdint.h>
#define M10V_DIRECTORY_COUNT 37u
#define M10V_DIRECTORY_GROUPS 5u
#define M10V_DIRECTORY_GROUP_RESOURCE 1129u
static const struct {uint16_t id;uint8_t group;char name[24];} m10v_directory[]={
{33,0,"800T"},
{66,0,"5207"},
{62,0,"5219"},
{78,0,"5203"},
{298,0,"5213"},
{77,0,"2460"},
{69,1,"Portra 160"},
{37,1,"Portra 400"},
{70,1,"Fuji Industrial 100"},
{73,1,"Fuji C200"},
{56,1,"Fuji Superia 200"},
{36,1,"Fuji Pro 400H"},
{35,1,"Kodak Gold 200"},
{58,1,"Kodak UltraMax 400"},
{74,1,"ProImage 100"},
{34,1,"Ektar 100"},
{71,1,"Lucky C200"},
{67,1,"Harman Phoenix II"},
{68,1,"Harman Red"},
{292,1,"Lomography"},
{75,2,"T-Max 100"},
{299,2,"Tri-X 400"},
{300,2,"Ilford Delta 100"},
{301,2,"Ilford Pan 400"},
{302,2,"Rollei Infrared 400"},
{303,2,"Ilford SFX 200"},
{304,2,"Fomapan 400"},
{305,2,"CatLABS X Film 80"},
{289,3,"Kodak Charmera"},
{72,3,"CCD"},
{293,3,"Polaroid"},
{296,3,"Cyanotype"},
{290,3,"Pixel Worlds"},
{76,3,"Aerochrome"},
{291,4,"Leica Monochrome"},
{297,4,"German Cool"},
{65,4,"GR2"},
};
static const uint8_t m10v_directory_first[6]={0,6,20,28,34,37};
static inline const char *m10v_directory_name(uint32_t id){for(uint32_t i=0;i<M10V_DIRECTORY_COUNT;i++)if(m10v_directory[i].id==id)return m10v_directory[i].name;return 0;}
#endif
