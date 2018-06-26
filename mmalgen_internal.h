/*
 * Copyright (c) 2018 Sugizaki Yukimasa (ysugi@idein.jp)
 * All rights reserved.
 *
 * This software is licensed under a Modified (3-Clause) BSD License.
 * You should have received a copy of this license along with this
 * software. If not, contact the copyright holder above.
 */

#ifndef MMALGEN_INTERNAL_H_
#define MMALGEN_INTERNAL_H_

#include <interface/mmal/mmal.h>
#include <interface/mmal/util/mmal_connection.h>
#include <interface/mmal/util/mmal_util_params.h>
#include <stdio.h>
#include <stdlib.h>


#define check_mmal(x) \
    do { \
        MMAL_STATUS_T status = (x); \
        if (status != MMAL_SUCCESS) { \
            fprintf(stderr, "%s:%d: MMAL call failed: 0x%08x\n", \
                    __FILE__, __LINE__, status); \
            return 1; \
        } \
    } while (0)


static inline MMAL_STATUS_T set_port_format(MMAL_PORT_T *port,
        const MMAL_FOURCC_T encoding, const int width, const int height)
{
    port->format->encoding = encoding;
    port->format->es->video.width  = VCOS_ALIGN_UP(width,  32);
    port->format->es->video.height = VCOS_ALIGN_UP(height, 16);
    port->format->es->video.crop.x = 0;
    port->format->es->video.crop.y = 0;
    port->format->es->video.crop.width  = width;
    port->format->es->video.crop.height = height;
    return mmal_port_format_commit(port);
}

static inline MMAL_STATUS_T set_port_displayregion_fullscreen(MMAL_PORT_T *port,
        const _Bool is_fullscreen)
{
    MMAL_DISPLAYREGION_T displayregion = {
        {MMAL_PARAMETER_DISPLAYREGION, sizeof(displayregion)},
        .fullscreen = !!is_fullscreen,
        .set = MMAL_DISPLAY_SET_FULLSCREEN,
    };
    return mmal_port_parameter_set(port, &displayregion.hdr);
}

static inline MMAL_STATUS_T set_port_displayregion_rect(MMAL_PORT_T *port,
        const int x, const int y, const int width, const int height)
{
    MMAL_RECT_T rect = {
        .x = x, .y = y, .width = width, .height = height,
    };
    MMAL_DISPLAYREGION_T displayregion = {
        {MMAL_PARAMETER_DISPLAYREGION, sizeof(displayregion)},
        .dest_rect = rect,
        .fullscreen = 0,
        .set = MMAL_DISPLAY_SET_DEST_RECT | MMAL_DISPLAY_SET_FULLSCREEN,
    };
    return mmal_port_parameter_set(port, &displayregion.hdr);
}

static inline MMAL_STATUS_T set_port_video_source_pattern(MMAL_PORT_T *port,
        const MMAL_SOURCE_PATTERN_T pattern, const uint32_t param)
{
    MMAL_PARAMETER_VIDEO_SOURCE_PATTERN_T source_pattern = {
        {MMAL_PARAMETER_VIDEO_SOURCE_PATTERN, sizeof(source_pattern)},
        .pattern = pattern,
        .param = param,
    };
    return mmal_port_parameter_set(port, &source_pattern.hdr);
}

static void cb_nop(MMAL_PORT_T *port, MMAL_BUFFER_HEADER_T *buffer)
{
#ifdef MMALGEN_DEBUG
    fprintf(stderr, "%s is called by %s\n", __func__, port->name);
#else
    (void) port;
#endif
    mmal_buffer_header_release(buffer);
}

typedef void (*hook_peep_buffer_t)(void*);
typedef void (*hook_edit_buffer_t)(void*, void*);
struct connection_callback_context {
    MMAL_PORT_T *out_port, *in_port;
    MMAL_POOL_T *out_pool, *in_pool;
    hook_peep_buffer_t hook_peep_buffer;
    hook_edit_buffer_t hook_edit_buffer;
};

#if 0
static void cb_conn_out_port(MMAL_PORT_T *port, MMAL_BUFFER_HEADER_T *buffer)
{
    struct connection_callback_context *ctx = port->userdata;

    /* Callback is not set for tunneled connection! */
    check_assert(ctx->out_pool != NULL);

    /* Hook: Peep buffer */
    if (ctx->hook_peep_buffer != NULL)
        ctx->hook_peep_buffer(buffer->data);

    if (ctx->in_pool != NULL) {
        /* Hook: Edit buffer */
        in_buffer = mmal_queue_get(ctx->in_pool->queue);
        check_assert(in_buffer != NULL);
        ctx->hook_edit_buffer(in_buffer->data, buffer->data);

        in_buffer->flags |= MMAL_BUFFER_HEADER_FLAG_EOS;
        check_mmal(mmal_port_send_buffer(ctx->in_port, in_buffer));
        check_mmal(mmal_port_send_buffer(ctx->out_port, in_
        in_buffer->flags ^= MMAL_BUFFER_HEADER_FLAG_EOS;
    }
}

static inline MMAL_STATUS_T connection_create(
        MMAL_PORT_T *out_port, MMAL_PORT_T *in_port,
        hook_peep_buffer_t hook_peep_buffer,
        hook_edit_buffer_t hook_edit_buffer)
{

    out_port->buffer_num = MMAL_MAX(out_port->buffer_num_recommended,
            out_port->buffer_num_min);
    out_port->buffer_size = MMAL_MAX(out_port->buffer_size_recommended,
            out_port->buffer_size_min);
    in_port->buffer_num = MMAL_MAX(in_port->buffer_num_recommended,
            in_port->buffer_num_min);
    in_port->buffer_size = MMAL_MAX(in_port->buffer_size_recommended,
            in_port->buffer_size_min);

    if (hook_peep_buffer == NULL && hook_edit_buffer == NULL) {
        /* Tunnelling */
        check_mmal(mmal_port_connect(out_port, in_port));
        check_mmal(mmal_port_enable(out_port));
        /* Input port will be enabled automatically. */
    } else if (hook_peep_buffer != NULL && hook_edit_buffer == NULL) {
        /* Create a single pool on output port. */
        out_pool = mmal_port_pool_create(out_port, out_port->buffer_num,
                out_port->buffer_size);
        check_assert(out_pool != NULL);
        in_pool = NULL;
    } else { /* hook_edit_buffer != NULL */
        /* Create pools on input/output pools. */
    }
}
#endif

#endif /* MMALGEN_INTERNAL_H_ */
